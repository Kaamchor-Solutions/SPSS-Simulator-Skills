# Security policy

## Scope

Security reports are welcome for the Python helper, documentation, and repository configuration. This project is not intended to store, upload, or transmit datasets. The host LLM platform may have separate data handling and security behavior.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue. If enabled, use **Private vulnerability reporting / Security Advisories** on the GitHub repository. Otherwise, contact the repository maintainers privately using a contact method listed on the repository profile. Include a description, impact, affected version/commit, reproduction steps, and a safe proof of concept. Do not include real private datasets, credentials, or personal data.

The maintainers will acknowledge reports as reasonably possible, investigate, and coordinate a fix and disclosure. No response-time SLA is promised until the project establishes one. Please give maintainers a reasonable opportunity to address a report before public disclosure.

## Safe data handling

- Do not commit real research or personal data, even if used as a “sample.”
- Use fabricated, minimal fixtures in tests and bug reports.
- Do not upload sensitive files to an LLM or external service unless authorized and covered by an appropriate privacy/security review.
- Review outputs before sharing; summaries may still reveal sensitive information in small groups.
