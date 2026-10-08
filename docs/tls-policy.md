# HTTPS certificate key policy

The Home Assistant and Gateway clients first perform ordinary certificate-chain
and hostname verification using HTTPX's default CA bundle. Before either client
sends HTTP headers or a body, its own TLS socket then checks **the same verified
chain**, including the trust anchor. The check does not rebuild a different chain
or open a second connection. Redirects and environment proxies remain disabled;
HTTP on an explicitly configured trusted local network remains supported.

The supported public-key profiles are RSA (including RSA-PSS) with an exact
modulus of at least 2048 bits; DSA with p at least 2048 and q at least 224 bits;
Ed25519 and Ed448; and these named elliptic curves at 224 bits or above:
secp224r1, secp256r1, secp256k1, secp384r1, secp521r1, brainpoolP256r1,
brainpoolP384r1 and brainpoolP512r1. Unknown algorithms/curves, explicit EC
parameters, unavailable chain APIs, incomplete metadata and chains longer than
16 certificates are rejected. Each encoded certificate is limited to 64 KiB.

OpenSSL remains responsible for signatures, chain construction, certificate
validity, hostname matching, negotiated ciphers, key exchange and TLS randomness.
The additional policy reads public-key metadata with maintained `pyasn1` and
`pyasn1-modules` schemas; it does not implement a cryptographic primitive or a
custom DER decoder. The frozen lock requires `pyasn1` 0.6.4 or later, whose
[security fixes](https://pyasn1.readthedocs.io/en/stable/changelog.html) bound
nested structures, tags and encoded lengths. The schemas follow
[RFC 5280](https://www.rfc-editor.org/rfc/rfc5280),
[RFC 4055](https://www.rfc-editor.org/rfc/rfc4055),
[RFC 5480](https://www.rfc-editor.org/rfc/rfc5480),
[RFC 5639](https://www.rfc-editor.org/rfc/rfc5639) and
[RFC 8410](https://www.rfc-editor.org/rfc/rfc8410).

CPython 3.12 exposes the verified chain on its internal SSL object; newer
interpreters may provide the public DER-chain API. The runtime integration must
be retested after interpreter, HTTPX or OpenSSL upgrades. A missing chain API
fails closed instead of silently relying on rounded OpenSSL security estimates.
In particular, the previous default accepted a trusted RSA-2047 root in native
loopback tests; ordinary verification alone did not enforce this exact minimum.

## Upgrade and deployment

Replace weak endpoint or CA certificates with an appropriate supported profile
before upgrading. Do not disable verification or add an unverified replacement
root to work around rejection. Keep hostname/SAN and the deployment's existing
trust policy correct. No certificate or trust-store migration runs automatically.

The Venus archive still contains only pure Python runtime dependencies. The new
ASN.1 libraries are included by the existing frozen, hash-checked bundle builder;
there is no new native wheel, Rust compiler or firmware-package requirement.
`cryptography` belongs only to the development test group for generating
synthetic certificates and is not included in the runtime bundle. The installer
retains its existing import check before stopping a running service.

The loopback tests exercise both real client classes, TLS 1.2/1.3, weak keys in
leaf/intermediate/root positions, exact RSA-2047 rejection, accepted RSA/EC
chains, and hostname/trust failures. Negative peers are calibrated separately
with a lower-policy test client. Metadata tests cover each supported algorithm
and malformed/unknown inputs. These checks do not establish hardware acceptance,
CA-store quality, device entropy or security of an external reverse proxy.
