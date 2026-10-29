## How to report a vulnerability

Please **do not open a public issue**. Report privately via
[GitHub Security Advisories](https://github.com/vicmacabre/aperture/security/advisories/new)
or email **security@example.com**. <!-- TODO: replace before PyPI release -->

Include: affected version, reproduction steps, and impact assessment.

# Security model

Aperture sends hidden-instruction probes to systems you point it at. Treat it like any other security tool.

| Threat | Mitigation | Residual risk |
|---|---|---|
| Used against a system you do not own | `authorized_by` is required in config; docs and README state the rule | Cannot be enforced technically |
| Used as an attack kit | Probes carry only a fixed harmless instruction plus a random canary; carriers transform it and cannot author content | A plugin carrier is arbitrary code you chose to install |
| Malicious curl command (file read/write, proxy, TLS off) | Strict tokenizer, never a shell, never executed; `-o -O -T -F -x -K -k @file` rejected; tested | Only flags on the allow-list work |
| SSRF via configured URL | Metadata/link-local/reserved addresses always blocked; private and loopback need `allow_private = true`; http(s) only; redirects refused | DNS rebinding between check and request |
| Secret leakage | Keys come from env vars, are tracked and redacted from errors and output; run files hold probes and responses, never credentials | Responses may contain whatever the target echoes: `.aperture/` is git-ignored |
| Malicious target response | Responses are data: size-capped, never executed; the HTML report escapes everything and never prints raw (invisible) fragments | None known |
| Hostile pipeline file | None: it is your own code. Child-process isolation is for crashes and hangs, **not** a sandbox | Run only pipeline files you trust |
| Hostile third-party carrier | Contract tests run against every registered carrier | It still runs in-process: install plugins you trust |

Report vulnerabilities privately to the maintainer before opening a public issue.
