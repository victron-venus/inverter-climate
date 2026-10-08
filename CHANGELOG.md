# Changelog

## [0.4.0] - Development line

### Release overview

Coordinates climate setpoints with measured energy through Home Assistant and Venus OS. The existing README documents configuration and external interfaces for this development line.

### Maintenance

- Keep native installer terminal-exit detection linear for long whitespace-heavy `rc.local` lines while preserving existing shell text and hook placement.
- Publish reviewed release notes from the exact source commit used to build each candidate, preserving build provenance.
- Document contribution checks, confidential security reporting and the project-specific trust boundaries.

### Upgrade

These maintenance changes do not introduce a configuration or data migration. Retain local configuration and credentials when using the documented update procedure. Validate the candidate on an isolated system before production use; automated checks do not establish hardware acceptance.

### Security

Private vulnerability reporting and response policy are documented in SECURITY.md. This maintenance update strengthens release evidence and review instructions; it does not replace deployment authentication, network isolation or independent equipment safeguards. No new project CVE is announced by these changes.
