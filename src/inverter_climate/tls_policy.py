"""Check public-key sizes after the same socket's ordinary TLS verification.

This parses public certificate metadata only. OpenSSL still verifies signatures,
the trust chain and hostname. Pure-Python ASN.1 packages preserve the Venus bundle
ABI; no project code implements DER decoding or a cryptographic primitive.
"""

from __future__ import annotations

import ssl

import httpx
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ
from pyasn1_modules import rfc3279, rfc5280, rfc5480, rfc8017

MAX_CERTIFICATE_BYTES = 64 * 1024
MAX_CHAIN_CERTIFICATES = 16
_RSA = {"1.2.840.113549.1.1.1", "1.2.840.113549.1.1.10"}
_NAMED_CURVE_BITS = {
    "1.2.840.10045.3.1.1": 192,  # secp192r1
    "1.3.132.0.33": 224,  # secp224r1
    "1.2.840.10045.3.1.7": 256,  # secp256r1
    "1.3.132.0.10": 256,  # secp256k1
    "1.3.132.0.34": 384,  # secp384r1
    "1.3.132.0.35": 521,  # secp521r1
    "1.3.36.3.3.2.8.1.1.7": 256,  # brainpoolP256r1
    "1.3.36.3.3.2.8.1.1.11": 384,  # brainpoolP384r1
    "1.3.36.3.3.2.8.1.1.13": 512,  # brainpoolP512r1
}


def _decode_complete(data: bytes, schema):
    if not isinstance(data, bytes) or not data or len(data) > MAX_CERTIFICATE_BYTES:
        raise ValueError("Certificate metadata exceeds the supported bounds")
    value, remaining = decode(data, asn1Spec=schema, decodeOpenTypes=False)
    if remaining or not value.isValue:
        raise ValueError("Incomplete certificate metadata")
    return value


def _strong_rsa(key: bytes) -> bool:
    public = _decode_complete(key, rfc8017.RSAPublicKey())
    modulus, exponent = int(public["modulus"]), int(public["publicExponent"])
    return modulus > 0 and modulus.bit_length() >= 2048 and exponent >= 3 and exponent % 2 == 1


def _strong_dsa(key: bytes, parameters: bytes) -> bool:
    values = _decode_complete(parameters, rfc3279.Dss_Parms())
    p, q, g = (int(values[name]) for name in ("p", "q", "g"))
    y = int(_decode_complete(key, univ.Integer()))
    return p > 0 and p.bit_length() >= 2048 and q > 0 and q.bit_length() >= 224 and g > 0 and y > 0


def _strong_public_key(info) -> bool:
    algorithm = str(info["algorithm"]["algorithm"])
    parameters = info["algorithm"]["parameters"]
    bits = info["subjectPublicKey"]
    if not bits or len(bits) % 8:
        return False
    key = bits.asOctets()
    if algorithm in _RSA:
        return _strong_rsa(key)
    if algorithm == "1.2.840.10045.2.1":
        curve = _decode_complete(parameters.asOctets(), rfc5480.ECParameters())
        return (
            curve.getName() == "namedCurve"
            and _NAMED_CURVE_BITS.get(str(curve["namedCurve"]), 0) >= 224
        )
    if algorithm == "1.2.840.10040.4.1":
        return _strong_dsa(key, parameters.asOctets())
    if algorithm in {"1.3.101.112", "1.3.101.113"}:
        return not parameters.hasValue() and len(key) == (32 if algorithm.endswith("112") else 57)
    return False


def certificate_key_is_strong(der: bytes) -> bool:
    """Read the complete X.509 schema and its public key, never unverified ASN.1 guesses."""
    certificate = _decode_complete(der, rfc5280.Certificate())
    return _strong_public_key(certificate["tbsCertificate"]["subjectPublicKeyInfo"])


def verify_key_lengths(connection: ssl.SSLSocket) -> None:
    """Fail closed when the verified chain or supported key metadata is unavailable."""
    try:
        if connection.context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError("Ordinary certificate verification is required")
        get_chain = getattr(connection, "get_verified_chain", None)
        if get_chain is None:
            # CPython 3.12 exposes this on its internal SSL object. Later Python
            # releases expose the public DER API above. Both refer to this TLS session.
            get_chain = getattr(getattr(connection, "_sslobj", None), "get_verified_chain", None)
        if get_chain is None:
            raise ValueError("Verified certificate chain is unavailable")
        chain = get_chain()
        if not isinstance(chain, (list, tuple)) or not 0 < len(chain) <= MAX_CHAIN_CERTIFICATES:
            raise ValueError("Verified certificate chain exceeds supported bounds")
        for certificate in chain:
            if isinstance(certificate, bytes):
                der = certificate
            else:
                pem = certificate.public_bytes()
                if not isinstance(pem, str) or len(pem) > MAX_CERTIFICATE_BYTES * 2:
                    raise ValueError("Invalid verified certificate representation")
                der = ssl.PEM_cert_to_DER_cert(pem)
            if not certificate_key_is_strong(der):
                raise ValueError("Verified certificate key is below the required size")
    except (AttributeError, TypeError, ValueError, PyAsn1Error, RecursionError):
        raise ssl.SSLError("TLS certificate key policy validation failed") from None


class _VerifiedSocket(ssl.SSLSocket):
    def do_handshake(self, block: bool = False) -> None:
        super().do_handshake(block=block)
        try:
            verify_key_lengths(self)
        except ssl.SSLError:
            self.close()
            raise


def verified_context() -> ssl.SSLContext:
    """Use HTTPX's existing CA/default policy with a socket-local post-handshake check."""
    context = httpx.create_ssl_context(verify=True, trust_env=False)
    context.sslsocket_class = _VerifiedSocket
    return context
