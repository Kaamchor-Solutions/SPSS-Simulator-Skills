# Changelog

## Unreleased

- Add on-demand protocols and routing for all existing/new procedures.
- Fix t-test typed-label diagnostics and paired SPSS syntax sign; document Type 7 quartiles.
- Preserve default singleton dropping for compatibility; add explicit retain/error policy.
- Add Levene, pooled t, source-preserving recode/range/dummy preparation.
- Add rank/Fisher tests, Welch ANOVA and Tukey/Games-Howell pairwise inference.
- Add restricted two-way/ANCOVA, one-factor repeated ANOVA with GG/HF, and PCA/varimax.
- Add noisy library/invalid fixtures and a published-SPSS Duncan omnibus reference.
- CI runs pytest; no licensed-SPSS or whole-procedure parity claim.


## Formatted output layer

- `--format text|markdown` on `scripts/analyze.py` prints SPSS-style tables for every procedure; default JSON output is unchanged.
- `--plots-dir` writes histogram/bar/box/error-bar/scatter/residual charts (matplotlib).
- New `scripts/spss_report.py` builds a Markdown or self-contained HTML report (executive result, tables, charts, APA-style interpretation, limitations, SPSS syntax, reproducibility).
- Additive JSON fields: ANOVA `sum_of_squares`; linear `model_summary` and `beta_standardized`; logistic `model_fit` and `classification`.
- `analyze.run_request()` factored out of the CLI for reuse.
- `SKILL.md` gains a "Producing SPSS-like output" section; docs and `docs/sample-output.txt` added.
- New `tests/test_formatting.py` (known-answer tables, plot data, PNG validity, report structure, JSON contract).

## Second-audit correctness pass

- Reject repeated item/predictor/correlation selections, empty selections and nonfinite inputs.
- Prevent ANOVA group-name collisions and intercept/predictor name collisions.
- Mark undefined tests and nonconvergent/separated logistic fits invalid.
- Clarify per-variable/listwise/pairwise policies and overlapping audit counts.
- Add 15 second-audit tests, including both infinity signs across 11 procedure variants.
- Record statsmodels/pyreadstat versions when installed.


This project follows a simple Keep a Changelog-style format. Versions use Semantic Versioning where practical.

## [Unreleased]

### Fixed
- ANOVA no longer silently excludes groups with fewer than two usable observations; dropped groups are reported with their usable N.
- Non-numeric values coerced to missing are no longer silent: every procedure that drops rows, groups, or values reports a `data_audit` object (`rows_total`, `rows_used`, `exclusions` with reasons, counts, and samples).
- Independent t-test now rejects duplicate group selections (for example `["control","control"]`).
- `.sav` files are now read with their underlying codes (value labels are not applied), so labelled 0/1 variables stay numeric and binary logistic regression works on them; code and documentation now agree.
- Documentation no longer claims uniform listwise deletion: correlation is documented as pairwise per variable pair, with per-pair N and dropped counts in the output.
- The getting-started examples now reference columns that exist in the shipped demo data, and every documented request is a runnable file in `examples/` covered by a test.

### Added
- `data_audit` exclusion reporting across t-tests, ANOVA, correlation, regression, Cronbach's alpha, and crosstabs.
- `examples/demo-paired.csv`, `examples/demo-items.csv`, and runnable request files for every supported procedure.
- Known-answer and edge-case tests for every procedure: descriptives, inventory, frequencies, crosstab/chi-square, Welch and paired t-tests, ANOVA, Pearson/Spearman, OLS, logistic regression, and Cronbach's alpha, plus regression tests for the fixed bugs (silent ANOVA group drops, silent numeric coercion, duplicate groups, labelled `.sav` handling) and a test that runs every shipped example request.
- `describe` and `inventory` now flag mixed columns where some values parse as numeric and some do not.

### Changed
- Flattened the repository layout: all project files now live at the repository root instead of the nested `spss-simulator-opensource/` folder.
- Upgraded the README with badges, a table of contents, a repository-layout overview, a citation section, and corrected license wording.

### Added
- GitHub issue templates, a pull request template, and a CI workflow that runs the unit tests.
- `templates/analysis-report-template.md` mirroring the default report format in `SKILL.md`.
- Root `.gitignore` covering Python artifacts, generated output, and editor files.
- Repository URL and corporate author in `CITATION.cff`.

## [0.1.0] - 2026-10-08

### Added
- Portable SPSS-style LLM skill instructions and procedure guide.
- Python companion for inventory, descriptive summaries, frequencies, crosstabs, t-tests, one-way ANOVA, correlations, OLS/logistic regression, and Cronbach’s alpha.
- Getting-started, methods/limitations, contribution, security, and conduct documentation.
- Example request and fabricated demonstration data.
