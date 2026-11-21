# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 1.0.x | ✓ |
| < 1.0 | – (unreleased) |

## Reporting a vulnerability

**Do not open a public issue for an exploitable vulnerability.**

Report it privately through GitHub: on the repository page open **Security → Report a vulnerability**
(GitHub private vulnerability reporting). The maintainer needs to enable this in *Settings → Code security*.
If it is not available, contact the maintainer through the GitHub profile
[@pavangemmanjunath-cell](https://github.com/pavangemmanjunath-cell) and ask for a private channel
without including the details.

## What to include

- affected version or commit;
- description of the vulnerability and the affected component (API, front end, scripts, CI);
- steps to reproduce or a proof of concept;
- impact (what an attacker can do);
- suggested mitigation, if you have one.

## Scope notes

The API has no authentication and is designed for local or trusted-network use. Denial of service through
many concurrent what-if jobs is mitigated by `QH2DC_MAX_WORKERS` and input bounds but not eliminated; run
the service behind an authenticating reverse proxy with rate limits before exposing it publicly.

## Response expectations

This is a research project maintained on a best-effort basis. Reports will be acknowledged and assessed
as soon as practicable; no response-time guarantee is given. Fixes are released as patch versions and
credited unless you ask otherwise.
