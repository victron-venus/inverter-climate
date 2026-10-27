# Changelog

## [0.4.6] - 2026-10-27

### Changed

- Refresh the pinned Python runtime and uv build images used by the application container.
- Keep dependency locking and the existing climate-control configuration unchanged.

### Upgrade

Use the existing container update procedure, preserving climate-control configuration and persistent data. Retain the previous immutable image for rollback. No configuration or data migration is required.

### Security

Keep certificate and hostname verification enabled and retain the pinned dependency and image inputs. This image maintenance does not change authorization or transport trust requirements and does not establish live thermostat or device acceptance.

## [0.4.5] - 2026-10-20

### Changed

- Update the locked certifi certificate bundle to 2026.10.19.
- Allow the release API status to catch up for up to five minutes while preserving exact run identity, attempt and required-check validation.
- Refresh the pinned Python 3.15 container image used for build and runtime.
- Align the release-candidate fuzz workflow and its runner with the reviewed shared CI revision; fuzz campaigns remain limited to public release candidates.

### Upgrade

No configuration or data migration is required. Preserve local configuration and retain the previous immutable release for rollback.

### Security

- Use uv 0.13.4 for CI, release packaging, and the container build stage to remove the distrusted emSign root from the build tool's own TLS trust store (GHSA-hq85-5cpj-mr62).

The certificate bundle removes the distrusted emSign ECC Root CA - G3 (GHSA-6q48-6c7w-9gw2). Certificate and hostname verification remain enabled. Images and workflows remain pinned, and all existing quality, security and RC fuzzing gates remain required. Offline checks do not establish live thermostat or device acceptance.

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
