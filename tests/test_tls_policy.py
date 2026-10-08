"""Synthetic loopback TLS and metadata bounds; no thermostat or trust-store writes."""

import socket
import ssl
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import certifi
import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from pyasn1.codec.der.encoder import encode
from pyasn1.type import univ
from pyasn1_modules import rfc3279, rfc5280, rfc5480, rfc8017

from inverter_climate import tls_policy as policy
from inverter_climate.clients import GatewayClient, HomeAssistantClient, IntegrationError

Key = rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey

CHAIN_CASES = (
    "strong",
    "strong-ec",
    "weak-leaf",
    "weak-intermediate",
    "weak-root",
    "weak-2047-root",
    "weak-ec-root",
)


def certificate(
    key: Key, name: str, issuer: x509.Certificate | None, issuer_key: Key, *, ca: bool
) -> x509.Certificate:
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer.subject if issuer else subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(hours=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=not ca,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=ca,
                crl_sign=ca,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), False
        )
    )
    if not ca:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), False
        ).add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]
            ),
            False,
        )
    return builder.sign(issuer_key, hashes.SHA256())


@pytest.fixture(scope="module")
def chains(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Path, Path, Path]]:
    directory = tmp_path_factory.mktemp("climate-synthetic-pki")
    result = {}
    for case in CHAIN_CASES:
        root_bits = {"weak-root": 1024, "weak-2047-root": 2047}.get(case, 2048)
        root_key: Key
        if case in ("strong-ec", "weak-ec-root"):
            curve = ec.SECP192R1() if case == "weak-ec-root" else ec.SECP256R1()
            root_key = ec.generate_private_key(curve)
        else:
            root_key = rsa.generate_private_key(65537, root_bits)
        root = certificate(root_key, case, None, root_key, ca=True)
        issuer, issuer_key = root, root_key
        intermediate = b""
        if case == "weak-intermediate":
            issuer_key = rsa.generate_private_key(65537, 1024)  # nosec B505 - rejected synthetic chain fixture
            issuer = certificate(issuer_key, "intermediate", root, root_key, ca=True)
            intermediate = issuer.public_bytes(serialization.Encoding.PEM)
        leaf_key: Key = (
            ec.generate_private_key(ec.SECP256R1())
            if case == "strong-ec"
            else rsa.generate_private_key(65537, 1024 if case == "weak-leaf" else 2048)
        )
        leaf = certificate(leaf_key, "localhost", issuer, issuer_key, ca=False)
        cert_file, key_file, ca_file = (
            directory / f"{case}.{suffix}" for suffix in ("pem", "key", "ca")
        )
        cert_file.write_bytes(leaf.public_bytes(serialization.Encoding.PEM) + intermediate)
        key_file.write_bytes(
            leaf_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        ca_file.write_bytes(root.public_bytes(serialization.Encoding.PEM))
        result[case] = cert_file, key_file, ca_file
    return result


@contextmanager
def peer(chain, version):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = version
    context.set_ciphers("DEFAULT:@SECLEVEL=0")
    context.load_cert_chain(*chain[:2])
    seen = {"bytes": b""}
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(5)

        def worker():
            try:
                raw, _ = listener.accept()
                with raw:
                    raw.settimeout(5)
                    with context.wrap_socket(raw, server_side=True) as stream:
                        seen["tls_version"] = stream.version()
                        while b"\r\n\r\n" not in seen["bytes"]:
                            part = stream.recv(4096)
                            if not part:
                                return
                            seen["bytes"] += part
                        stream.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}"
                        )
            except (ssl.SSLError, ConnectionResetError, BrokenPipeError) as exc:
                seen["transport_error"] = repr(exc)
            except Exception as exc:
                seen["unexpected"] = repr(exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            yield listener.getsockname()[1], seen
        finally:
            thread.join(6)
            assert not thread.is_alive()
            assert "unexpected" not in seen, seen


@pytest.mark.parametrize("client_class", [HomeAssistantClient, GatewayClient])
@pytest.mark.parametrize("version", [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3])
@pytest.mark.parametrize("case", [*CHAIN_CASES, "wrong-host", "untrusted"])
def test_actual_clients_reject_weak_chains_before_credentials(
    chains, monkeypatch, client_class, version, case
):
    chain = chains.get(case, chains["strong"])
    ca = chains["strong-ec"][2] if case == "untrusted" else chain[2]
    monkeypatch.setattr(certifi, "where", lambda: str(ca))
    with peer(chain, version) as (port, seen):
        host = "127.0.0.1" if case == "wrong-host" else "localhost"
        client = client_class(f"https://{host}:{port}", "synthetic-only")
        try:
            if case.startswith("strong"):
                assert client._object("GET", "api/config") == {}
            else:
                with pytest.raises(IntegrationError, match="failed or timed out"):
                    client._object("GET", "api/config")
        finally:
            client.close()
    if case.startswith("strong"):
        assert (
            seen["tls_version"]
            == {ssl.TLSVersion.TLSv1_2: "TLSv1.2", ssl.TLSVersion.TLSv1_3: "TLSv1.3"}[version]
        )
        assert b"Authorization: Bearer synthetic-only" in seen["bytes"]
    else:
        assert seen["bytes"] == b""


@pytest.mark.parametrize("version", [ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3])
@pytest.mark.parametrize("case", CHAIN_CASES)
def test_fixture_supports_verified_calibration(chains, monkeypatch, version, case):
    chain = chains[case]
    monkeypatch.setattr(certifi, "where", lambda: str(chain[2]))
    context = httpx.create_ssl_context(verify=True, trust_env=False)
    context.set_ciphers("DEFAULT:@SECLEVEL=0")
    with peer(chain, version) as (port, seen):
        with httpx.Client(trust_env=False, verify=context) as client:
            assert client.get(f"https://localhost:{port}/oracle").status_code == 200
    assert seen["bytes"].startswith(b"GET /oracle ")
    assert (
        seen["tls_version"]
        == {ssl.TLSVersion.TLSv1_2: "TLSv1.2", ssl.TLSVersion.TLSv1_3: "TLSv1.3"}[version]
    )


def public_certificate(key):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "metadata-only")])
    now = datetime.now(UTC)
    algorithm = (
        None
        if isinstance(key, (ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey))
        else hashes.SHA256()
    )
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .sign(key, algorithm)
        .public_bytes(serialization.Encoding.DER)
    )


@pytest.mark.parametrize("bits,expected", [(1024, False), (2047, False), (2048, True)])
@pytest.mark.parametrize("pss", [False, True])
def test_rsa_and_pss_spki_exact_modulus(bits, expected, pss):
    der = public_certificate(rsa.generate_private_key(65537, bits))
    if pss:
        # Metadata-only fixture: RSA and RSA-PSS use the same RSAPublicKey schema.
        cert = policy._decode_complete(der, rfc5280.Certificate())
        cert["tbsCertificate"]["subjectPublicKeyInfo"]["algorithm"]["algorithm"] = (
            univ.ObjectIdentifier("1.2.840.113549.1.1.10")
        )
        # An empty PSS parameter sequence selects the RFC 4055 defaults;
        # unlike rsaEncryption, RSASSA-PSS does not use ASN.1 NULL here.
        cert["tbsCertificate"]["subjectPublicKeyInfo"]["algorithm"]["parameters"] = encode(
            rfc8017.RSASSA_PSS_params()
        )
        der = encode(cert)
    assert policy.certificate_key_is_strong(der) is expected


@pytest.mark.parametrize(
    "curve,expected",
    [(ec.SECP192R1, False), (ec.SECP224R1, True), (ec.SECP256K1, True), (ec.SECP521R1, True)],
)
def test_named_ec_minimum(curve, expected):
    assert (
        policy.certificate_key_is_strong(public_certificate(ec.generate_private_key(curve())))
        is expected
    )


@pytest.mark.parametrize(
    "factory", [ed25519.Ed25519PrivateKey.generate, ed448.Ed448PrivateKey.generate]
)
def test_edwards_keys(factory):
    assert policy.certificate_key_is_strong(public_certificate(factory()))


@pytest.mark.parametrize("bits,expected", [(1024, False), (2048, True)])
def test_dsa_parameter_minimum(bits, expected):
    assert (
        policy.certificate_key_is_strong(public_certificate(dsa.generate_private_key(bits)))
        is expected
    )


def test_verified_chain_api_and_malformed_bounds(chains):
    der = ssl.PEM_cert_to_DER_cert(chains["strong"][2].read_text())
    context = ssl.create_default_context()
    policy.verify_key_lengths(SimpleNamespace(context=context, get_verified_chain=lambda: [der]))
    for invalid in (
        [],
        [der] * 17,
        [der + b"trailing"],
        [der[:-1]],
        [b"\x30\x80\x00\x00"],
        [b"x" * 65537],
    ):
        connection = SimpleNamespace(
            context=context, get_verified_chain=lambda value=invalid: value
        )
        with pytest.raises(ssl.SSLError, match="key policy"):
            policy.verify_key_lengths(connection)
    with pytest.raises(ssl.SSLError, match="key policy"):
        policy.verify_key_lengths(SimpleNamespace(context=context))


def test_context_preserves_default_policy_and_is_not_shared(monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent/ignored-environment-ca")
    baseline = httpx.create_ssl_context(verify=True, trust_env=False)
    first, second = policy.verified_context(), policy.verified_context()
    assert first is not second
    assert first.verify_mode == baseline.verify_mode == ssl.CERT_REQUIRED
    assert first.check_hostname == baseline.check_hostname is True
    assert first.minimum_version == baseline.minimum_version
    assert first.get_ciphers() == baseline.get_ciphers()
    assert first.get_ca_certs(binary_form=True) == baseline.get_ca_certs(binary_form=True)
    assert first.sslsocket_class is policy._VerifiedSocket


@pytest.mark.parametrize("change", ["unknown", "trailing-key", "negative-rsa", "unused-bits"])
def test_unsupported_or_malformed_spki_fails_closed(change):
    cert = policy._decode_complete(
        public_certificate(rsa.generate_private_key(65537, 2048)), rfc5280.Certificate()
    )
    info = cert["tbsCertificate"]["subjectPublicKeyInfo"]
    if change == "unknown":
        info["algorithm"]["algorithm"] = univ.ObjectIdentifier("1.2.3.4.5")
    elif change == "trailing-key":
        info["subjectPublicKey"] = univ.BitString.fromOctetString(
            info["subjectPublicKey"].asOctets() + b"extra"
        )
    elif change == "negative-rsa":
        key = policy._decode_complete(info["subjectPublicKey"].asOctets(), rfc8017.RSAPublicKey())
        key["modulus"] = -int(key["modulus"])
        info["subjectPublicKey"] = univ.BitString.fromOctetString(encode(key))
    else:
        info["subjectPublicKey"] = univ.BitString("101")
    der = encode(cert)
    socket = SimpleNamespace(context=ssl.create_default_context(), get_verified_chain=lambda: [der])
    with pytest.raises(ssl.SSLError, match="key policy"):
        policy.verify_key_lengths(socket)


def test_unknown_curve_and_weak_dsa_subgroup_are_rejected():
    cert = policy._decode_complete(
        public_certificate(ec.generate_private_key(ec.SECP256R1())), rfc5280.Certificate()
    )
    info = cert["tbsCertificate"]["subjectPublicKeyInfo"]
    parameters = rfc5480.ECParameters()
    parameters["namedCurve"] = univ.ObjectIdentifier("1.2.3.4.5")
    info["algorithm"]["parameters"] = encode(parameters)
    assert not policy.certificate_key_is_strong(encode(cert))
    cert = policy._decode_complete(
        public_certificate(dsa.generate_private_key(2048)), rfc5280.Certificate()
    )
    info = cert["tbsCertificate"]["subjectPublicKeyInfo"]
    parameters = policy._decode_complete(
        info["algorithm"]["parameters"].asOctets(), rfc3279.Dss_Parms()
    )
    parameters["q"] = (1 << 160) - 1
    info["algorithm"]["parameters"] = encode(parameters)
    assert not policy.certificate_key_is_strong(encode(cert))


def test_unverified_socket_is_rejected():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with pytest.raises(ssl.SSLError, match="key policy"):
        policy.verify_key_lengths(SimpleNamespace(context=context))
