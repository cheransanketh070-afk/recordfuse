# Security Policy

## Supported versions

Security fixes are applied to the latest minor release on the default branch.

## Reporting a vulnerability

Please do **not** open a public issue containing exploit details, secrets, or real personal data. Use GitHub's private security-advisory reporting flow after the repository is published. Include the affected version, impact, minimal reproduction, and any suggested mitigation. Maintainers should acknowledge a valid report promptly and coordinate disclosure after a fix is available.

## Deployment notes

The reference FastAPI service intentionally does not implement authentication or tenancy. Do not expose it directly to an untrusted network without an authenticated gateway, transport encryption, request/body limits, rate limiting, logging controls, and retention rules appropriate to the data. The application avoids logging raw records by default and caps request record count, but hosting controls remain the operator's responsibility.

See `docs/THREAT_MODEL.md` for application-specific risks around false merges, PII, pathological blocking buckets, and dependency security.
