# Architecture, security evidence and roadmap

## Getting started

Use [installation, configuration and observation-first operation](../README.md). The documented [contribution checks](../CONTRIBUTING.md) are the local validation entry point. [Release ownership](../RELEASING.md) separates automated qualification from acceptance on a target deployment.

## Architecture and boundaries

Configuration is parsed before service startup. `clients.py` bounds and validates Home Assistant/gateway responses; `models.py` and the controller turn observations into permitted climate actions. `storage.py` persists local state. `service.py` and the D-Bus device adapter own process and platform integration. Observation mode is the default; automatic actuation and native manual controls require their separate documented opt-ins.

## Security argument and operating assumptions

Home Assistant/gateway credentials authorize real equipment operations. Origins cannot carry embedded credentials, query strings or paths. HTTPX does not follow redirects or inherit proxy environment settings. `tls_policy.py` checks the verified chain from the same TLS socket before request headers can be sent: RSA >=2048, DSA p>=2048/q>=224 and supported EC curves >=224 bits. Standard OpenSSL/HTTPX implementations perform TLS and signature verification; ASN.1 helpers only read public metadata. SHA-256 creates a local storage identity, not an authentication verifier. Operator-supplied tokens are not generated or treated as password hashes by this service. HTTP is still supported for deliberately isolated local deployments; HTTPS is recommended wherever available.

`tests/test_tls_policy.py` exercises certificate boundaries, malformed chains and TLS behavior. Client/controller/model tests cover malformed observations, constrained commands, stale data and rejection paths. `scripts/ci.sh` runs Ruff, pytest, source/wheel builds, workflow/release contracts and Venus bundle construction. The release candidate fuzz target mutates the actual climate parser and temperature-command validator for 60 seconds; it neither contacts devices nor actuates them. See [fuzzing](fuzzing.md).

These controls limit identified risks; they do not constitute an exhaustive independent security assessment. A passing test or a dependency scan does not establish absence of defects. Keep operator credentials outside source archives and public issue reports. Follow [SECURITY.md](../SECURITY.md) for confidential reports.

## Quality and maintenance policy

Major functionality requires automated tests, bug fixes require focused regressions, and changed interfaces require documentation and release-note updates under [CONTRIBUTING.md](../CONTRIBUTING.md). Review must keep validation enabled and explain narrow exceptions. Use the repository lockfiles and the documented common build tools. Dependabot/dependency review and required source-analysis jobs provide recurring feedback; the maintainer investigates actual findings rather than equating a green job with an empty alert list.

## Roadmap and acknowledged gaps

Measure coverage across maintained runtime and release helpers, not just a narrow test selection. Add a documented independent recovery arrangement. Extend fault injection around platform startup/storage failures and retain platform acceptance records. Audit every externally supplied input before claiming complete Silver input validation. A bounded parser campaign does not prove control-system or electrical safety.

The [changelog](../CHANGELOG.md) records delivered behavior and upgrade impact; issues and pull requests record decisions. This roadmap is a prioritized maintenance direction, not a release-date promise. Current automated test counts and scans belong to their exact source revision and CI run. No whole-project 80% coverage, complete security assurance case, bit-for-bit reproducible build or comprehensive accessibility certification is claimed by this document.

## OpenSSF assessment

[The evidence index](openssf-evidence.md) connects the public practices to the official assessment. The live assessment is authoritative for the awarded level. Unverified criteria remain unknown or unmet, and Silver continuity remains unmet as documented in [governance](../GOVERNANCE.md).
