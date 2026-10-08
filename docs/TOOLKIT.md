# Toolkit provenance

## Selective toolkit maintenance

The existing vendored baseline is retained. The following behavior-preserving
changes are backported from [toolkit ba1e3e7](https://github.com/victron-venus/venus-os-ci-toolkit/commit/ba1e3e7810783dca5ba6dec85274e2df60bdeef1):

- ASCII-only NIGHTLY identity pattern.

The repository-specific imports, type annotations, policy and workflow inputs
remain authoritative; this is not a full generator upgrade.
