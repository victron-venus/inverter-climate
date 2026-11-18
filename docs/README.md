# Documentation

A Venus OS service that exposes climate control over D-Bus, with the device
contract, transport policy and release records.

## Understand it

- [Venus OS D-Bus device](dbus-device.md) — the paths and services continuous operation publishes.
- [HTTPS certificate key policy](tls-policy.md) — the verification the Home Assistant and Gateway clients perform.
- [Toolkit provenance](TOOLKIT.md) — the retained vendored baseline and the behaviour-preserving changes.

## Assurance

- [Architecture, security evidence and roadmap](project-assurance.md) — how the pieces fit and what the contribution checks cover.
- [OpenSSF Best Practices evidence: inverter-climate](openssf-evidence.md) — the index behind the assessment.

## Releases

- [Native release packaging](release-packaging.md) — what the shared CI toolkit produces for this service.
- [CI and release operations](release-workflow.md) — `.release-policy.json` and the required status.
- [Version plans and manifest synchronization](VERSIONING.md) — the versioning opt-in.
- [Release-candidate fuzz testing](fuzzing.md) — the illustrated RC fuzzing process.
- [Fuzzing release candidates](rc-fuzzing.md) — the reusable bounded fuzz workflow.
- [Release read recovery and rerun validation](release-read-safety.md) — the two fixes carried from the shared toolkit.
- [Early final-build runner check](runner-preflight.md) — why the check runs before the final build.
