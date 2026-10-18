# Changelog

## [0.4.4] - 2026-10-18

### Changed

- Refresh the pinned Python container image and shared CI workflows.

### Upgrade

Use the documented upgrade procedure and preserve local configuration and data. No configuration migration is required. Keep the previous immutable release available for rollback.

### Security

This maintenance release preserves the existing security and release-validation requirements. Publication does not deploy the service or establish physical-device acceptance.

## [0.4.3] - 2026-10-17

### Changed

- Keep shared JSONata runtime dependency updates enabled in Renovate.
- Link the maintained RC fuzzing process and results.

### Upgrade

Use the existing update procedure and preserve local configuration. This maintenance release changes dependency-update configuration, not the device configuration format.

### Security

Dependency automation remains enabled; this release does not claim a new runtime vulnerability fix or target-device acceptance.

## [0.4.2] - 2026-10-14

### Changed

- Validate each public release candidate with bounded, network-isolated fuzz campaigns against its exact source revision.
- Require positive engine execution counts, instrumented production code and validated seed corpora; retain source-bound reports and diagnostic evidence.
- Run deterministic seed and configuration checks in ordinary CI without starting mutation campaigns on betas.

### Upgrade

Use the existing installation procedure, preserve local configuration and keep the previous accepted package for rollback. This maintenance release updates release validation and does not change the application configuration format. Deployment and applicable device or integration acceptance remain separate from publication.

### Security

The release gate rejects absent or invalid fuzz evidence and unsafe seed inputs. No application vulnerability or new target-device acceptance is claimed by these tooling changes.

## [0.4.1] - Development line

### Release candidate validation

- Require bounded fuzzing on public release candidates, with source-bound reports and retained diagnostics; beta and ordinary CI do not run mutation campaigns.

### Release overview

Coordinates climate setpoints with measured energy through Home Assistant and Venus OS. The existing README documents configuration and external interfaces for this development line.

### Maintenance

- Update the pinned container toolchain to Python 3.14 and uv 0.13.0 while keeping reproducible dependency installation.
- Refresh shared CI workflow pins without enabling reserve runners by default.

- Keep native installer terminal-exit detection linear for long whitespace-heavy `rc.local` lines while preserving existing shell text and hook placement.
- Publish reviewed release notes from the exact source commit used to build each candidate, preserving build provenance.
- Document contribution checks, confidential security reporting and the project-specific trust boundaries.

### Upgrade

HTTPS integrations now reject verified certificate chains containing RSA keys below 2048 bits or other unsupported public-key profiles. Replace weak endpoint/CA certificates before upgrading; see [TLS policy](docs/tls-policy.md). The Venus bundle remains pure Python and contains the new locked metadata-decoder dependencies. These changes do not introduce a configuration or data migration. Retain local configuration and credentials when using the documented update procedure. Validate the candidate on an isolated system before production use; automated checks do not establish hardware acceptance.

### Security

Home Assistant and Gateway HTTPS connections now enforce exact public-key sizes across the same connection's verified certificate chain, including its trust anchor, before sending authorization or application data. Ordinary hostname and trust verification remain enabled.

Private vulnerability reporting and response policy are documented in SECURITY.md. This maintenance update strengthens release evidence and review instructions; it does not replace deployment authentication, network isolation or independent equipment safeguards. No new project CVE is announced by these changes.
