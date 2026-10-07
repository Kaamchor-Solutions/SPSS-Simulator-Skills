# Contributing

Thank you for considering a contribution. Please keep this project transparent, reproducible, privacy-conscious, and clear about what it does not implement.

## Before opening an issue

- Search existing issues and pull requests.
- For analysis questions, include the exact procedure, variable roles/types, design, missing-data rule, expected behavior, and software versions.
- Never attach real sensitive data. Create a minimal fabricated dataset that reproduces the issue.
- For security reports, follow [`SECURITY.md`](SECURITY.md), not a public issue.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

Run the smoke tests:

```bash
python -m unittest discover -s tests -v
```

## Pull-request expectations

- Keep changes focused and explain the user problem they solve.
- Add or update tests for changed calculations, file handling, and edge cases.
- State assumptions, missing-data behavior, effect-size conventions, degrees of freedom, confidence-interval method, and tail direction for new inferential procedures.
- Validate calculations against an independent trusted implementation or hand-checkable fixture; document discrepancies rather than asserting SPSS equivalence.
- Update `SKILL.md`, references, `docs/methods-and-limitations.md`, examples, and `CHANGELOG.md` when behavior or user-facing scope changes.
- Do not commit private data, credentials, generated results containing personal data, virtual environments, or local configuration.
- Avoid describing this project as IBM SPSS or a full replacement. Clearly label unsupported methods and any unexecuted results.

## Contribution process

1. Fork the repository and create a focused branch.
2. Make the smallest clear change and add a minimal test.
3. Run the tests and review generated output.
4. Open a pull request with motivation, summary, test evidence, limitations, and any changes to statistical interpretation.

By submitting a contribution, you agree that it may be distributed under the project’s [MIT License](LICENSE).