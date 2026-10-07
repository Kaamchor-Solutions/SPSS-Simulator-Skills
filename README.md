# SPSS Simulator

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](scripts/requirements.txt)
[![Tests](https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills/actions/workflows/tests.yml/badge.svg)](https://github.com/Kaamchor-Solutions/SPSS-Simulator-Skills/actions/workflows/tests.yml)
[![Code of Conduct](https://img.shields.io/badge/code%20of%20conduct-Contributor%20Covenant-ff69b4.svg)](CODE_OF_CONDUCT.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**A portable, LLM-guided workflow for transparent, SPSS-style statistical analysis.** It is not IBM SPSS and does not reproduce every SPSS procedure or output.

The project combines an LLM skill (`SKILL.md`) with an optional Python helper for deterministic common calculations. The skill guides an assistant through file intake, variable definitions, analysis planning, data-preparation decisions, interpretation, and reproducibility. The helper reads supported data files and returns machine-readable JSON results.

> **Important:** An LLM skill is instructions, not an installation. Uploading it to an AI platform does not automatically grant file access, code execution, connectors, or statistical libraries. Results must be computed by the companion or another real statistical runtime; the assistant must never invent outputs.

## Table of contents

- [What it supports](#what-it-supports)
- [Quick start: run the Python helper](#quick-start-run-the-python-helper)
- [Use as an LLM skill](#use-as-an-llm-skill)
- [Repository layout](#repository-layout)
- [Statistical and product boundaries](#statistical-and-product-boundaries)
- [Privacy and security](#privacy-and-security)
- [Contributing](#contributing)
- [Citing this project](#citing-this-project)
- [License and trademark](#license-and-trademark)

## What it supports

The bundled Python companion (`scripts/analyze.py`) supports:

- Data inventory and missing/duplicate counts
- Descriptive summaries and category frequencies
- Crosstabs with Pearson chi-square and Cramér’s V
- Welch independent and paired t-tests
- Classical one-way ANOVA
- Pearson and Spearman correlations
- Ordinary least-squares (OLS) linear regression
- Binary logistic regression
- Cronbach’s alpha

Presentation layers (wrapping the same computed results): SPSS-style formatted tables (`--format text|markdown`), charts (`--plots-dir`), and a one-command Markdown/HTML report with interpretation, limitations and equivalent SPSS syntax (`scripts/spss_report.py`). See [`docs/sample-output.txt`](docs/sample-output.txt).

Input formats: CSV, TSV, Excel (`.xlsx`/`.xls`, depending on the installed engine), and SPSS `.sav` (with `pyreadstat`). Regression predictors in the helper must be numeric; binary logistic outcomes must be coded 0/1.

## Quick start: run the Python helper

Requires Python 3.10 or newer (tested with Python 3.11 and 3.13) and pip.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

Create `request.json`:

```json
{
  "file": "examples/demo.csv",
  "action": "describe",
  "variables": ["score", "age"]
}
```

Run the analysis:

```bash
python scripts/analyze.py --config request.json --output results.json
```

`examples/demo.csv` is fabricated solely to demonstrate the interface; it is not research data. Runnable request files for every supported procedure are in [`examples/`](examples/) (`describe-request.json`, `anova-request.json`, and so on); more context is in [`docs/getting-started.md`](docs/getting-started.md) and [`references/portable-runtime.md`](references/portable-runtime.md). Inferential procedures report exclusions in `data_audit`; describe and frequencies instead report per-variable missing counts.

Run the unit tests to verify your environment:

```bash
python -m unittest discover -s tests -v
```

## Use as an LLM skill

1. Upload `SKILL.md` to a platform that supports user-provided skills/instructions, or paste its contents into that platform’s equivalent project instructions.
2. Provide the relevant procedure guide in [`references/procedure-guide.md`](references/procedure-guide.md) when the platform does not load linked files automatically.
3. Upload a data file only through the platform’s supported, authorized file workflow. If the platform cannot run code, ask the assistant to generate runnable syntax or code instead of claiming analysis was executed.
4. Confirm variable labels, missing-value codes, group definitions, data design, and any transformations before relying on results.

The precise import steps differ by platform. This repository does not promise compatibility with every vendor’s “skill” format.

## Repository layout

```text
.
├── SKILL.md                      # LLM skill instructions (upload or paste into an AI platform)
├── scripts/                      # analyze.py, spss_format.py, spss_plots.py, spss_report.py
│   ├── analyze.py                # Deterministic Python companion (JSON in → JSON out)
│   └── requirements.txt
├── docs/                         # Getting started; methods and limitations
├── references/                   # Procedure guide and portable-runtime notes
├── examples/                     # Fabricated demo data and sample requests
├── templates/                    # Reusable analysis-report templates
├── tests/                        # Unit tests (unittest)
├── .github/                      # Issue/PR templates and CI workflow
├── CHANGELOG.md
├── CITATION.cff
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── SECURITY.md
```

## Statistical and product boundaries

This project is a transparent starter tool, not a full SPSS clone, a substitute for a statistician, or a guarantee of scientifically appropriate results. The companion does not currently implement survey weights, filters, split-file state, user-defined SPSS missing values/value labels, multiple imputation, robust/clustered standard errors, exact tests, post-hoc families, mixed models, survival analysis, or broad SPSS syntax execution. See [`docs/methods-and-limitations.md`](docs/methods-and-limitations.md).

The project does not establish causality, guarantee assumptions, or automatically infer the correct meaning of coded variables. Review the study design and analysis choices. Output may differ from IBM SPSS because procedures, options, defaults, versions, missing-data rules, and rounding differ.

## Privacy and security

Do not commit private datasets, credentials, identifying information, or analysis outputs containing sensitive data. The helper processes a file supplied by the user and writes summary JSON; it does not intentionally send data over the network. LLM platforms may process uploaded files under their own terms—review those terms and obtain authorization before uploading sensitive data. See [`SECURITY.md`](SECURITY.md).

## Contributing

Issues and pull requests are welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) first. Report vulnerabilities privately using the repository owner’s GitHub Security Advisories if enabled; see [`SECURITY.md`](SECURITY.md).

## Citing this project

If you use this software in research or reporting, please cite it using the metadata in [`CITATION.cff`](CITATION.cff). Citation formats can be validated or exported with [cffconvert](https://github.com/citation-file-format/cffconvert).

## License and trademark

This project is released under the [MIT License](LICENSE). “IBM” and “SPSS” are trademarks of their respective owners. This independent project is not affiliated with or endorsed by IBM.

## Validation and result status

Variable selections must be non-empty lists of distinct column names. Crosstab variables must be different. Numeric infinity values are rejected in requested columns (all columns for inventory), not silently treated as usable cases; explicitly correct or recode them first. No automatic recoding is performed.

Inspect `valid` before interpretation. Undefined inference (constant correlation, zero-variance differences/groups/item totals, insufficient crosstab categories) returns `valid: false`, a reason, and no usable test result. Correlation also marks invalid pairs individually. Logistic fits report convergence and are invalid when nonconvergent or separation warnings occur; numerical exceptions exit nonzero. JSON output does not by itself mean valid inference.

Audit counts are overlapping reason/variable incidences, not a disjoint partition. Do not sum exclusions to derive dropped rows. Use `rows_total - rows_used` for a procedure's unique dropped-row total; correlation instead reports each pair's N and dropped count and sets overall `rows_used` to null. ANOVA dropped-group `count` is the group's original row count; `usable_n` is its numeric, nonmissing outcome count. Describe and frequencies have per-variable missing counts rather than `data_audit`.
