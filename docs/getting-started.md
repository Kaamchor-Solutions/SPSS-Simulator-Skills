# Getting started

## 1. Set up the optional Python helper

Use Python 3.10+. From the project root:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

The default requirements include `pyreadstat`, which is only needed for SPSS `.sav` files. For Excel `.xlsx`, `openpyxl` is used. Reading older `.xls` workbooks may require an additional engine such as `xlrd`; convert the file to `.xlsx` if needed.

## 2. Inspect a dataset first

Create `request.json`:

```json
{"file":"examples/demo.csv","action":"inventory"}
```

Run:

```bash
python scripts/analyze.py --config request.json --output inventory.json
```

Review variable names, data types, unique counts, missing values, and duplicate-row counts. Confirm that numeric category codes, special missing-value codes, dates, IDs, and value labels have been interpreted correctly. The helper does not identify user-defined missing values in `.sav` files and does not apply SPSS value labels: labelled variables are read as their underlying codes, so confirm what each code means before analysis.

## 3. Request an analysis

Each request is UTF-8 JSON and contains the input `file`, one `action`, and action-specific fields. Paths are relative to the current working directory unless absolute. Excel can take a sheet name or index using `sheet`.

Every example below is also a runnable request file in `examples/` (for example `examples/describe-request.json`); run any of them from the project root with `python scripts/analyze.py --config examples/<name>.json`. The shipped demo data is `examples/demo.csv` (columns: `id, group, age, score, event`), `examples/demo-paired.csv` (`id, before, after`), and `examples/demo-items.csv` (`id, item1, item2, item3`).

### Descriptives and frequencies

```json
{"file":"examples/demo.csv","action":"describe","variables":["score","age"]}
```

```json
{"file":"examples/demo.csv","action":"frequencies","variables":["group"]}
```

### Crosstab

```json
{"file":"examples/demo.csv","action":"crosstab","row":"group","column":"event"}
```

### Independent Welch t-test

```json
{"file":"examples/demo.csv","action":"ttest","outcome":"score","group":"group","groups":["control","active"]}
```

`groups` is optional; if omitted, the helper uses the two observed nonmissing group values. Confirm their order, since the reported mean difference is first group minus second group. The two groups must be distinct.

### Paired t-test

```json
{"file":"examples/demo-paired.csv","action":"ttest","outcome":"after","paired_with":"before"}
```

The pairwise difference is `outcome - paired_with`. Rows must represent correctly matched pairs.

### One-way ANOVA

```json
{"file":"examples/demo.csv","action":"anova","outcome":"score","group":"group"}
```

This is classical one-way ANOVA; it does not run post-hoc tests or assess equal-variance robustness. Groups with fewer than two usable observations are excluded from the F test and reported in the output's `data_audit`.

### Correlation

```json
{"file":"examples/demo.csv","action":"correlation","variables":["age","score"],"method":"pearson"}
```

Use `"method":"spearman"` for Spearman rank correlation. Correlation is computed on complete pairs for each variable pair (pairwise), so per-pair N can differ when you request more than two variables; each pair reports its own N and dropped-row count. Inspect scatterplots and the study design before interpreting either result.

### Regression

```json
{"file":"examples/demo.csv","action":"regression","outcome":"score","predictors":["age"],"model":"linear"}
```

```json
{"file":"examples/demo.csv","action":"regression","outcome":"event","predictors":["age"],"model":"logistic"}
```

The helper requires numeric predictors. Encode categorical predictors deliberately, document the coding and reference category, and do not mistake numeric codes for continuous measurements. Logistic outcomes must be coded 0/1; the event value is 1.

### Cronbach’s alpha

```json
{"file":"examples/demo-items.csv","action":"alpha","variables":["item1","item2","item3"]}
```

Reverse-code items only according to the instrument’s scoring key before running this procedure. Alpha alone does not demonstrate unidimensionality or validity.

## 4. Read and preserve results

The helper writes JSON to stdout unless `--output` is specified. Keep the source dataset unchanged.

Describe and frequencies summarize each variable separately; inventory retains all rows. Regression and alpha use listwise-complete cases, independent t-tests and ANOVA use usable outcomes within selected groups, and crosstabs and paired t-tests omit incomplete pairs. Correlation is pairwise per variable pair. Inferential procedures carry a `data_audit` object: `rows_total`, `rows_used`, and an `exclusions` list naming what was excluded and why (missing values, non-numeric values coerced to missing, incomplete rows or pairs, groups with too few observations). A non-empty `exclusions` list is a warning: check it before relying on the analysis N. Record that policy and the resulting N.

The helper does not apply user-defined missing codes, filters, weights, or split-file settings.

Treat output as a calculation result, not as automatic validation of the research design. Check warnings, sample sizes, categories, assumptions, and model suitability before reporting. Refer to [`methods-and-limitations.md`](methods-and-limitations.md) for boundaries.

## 5. Formatted tables, charts and reports

The JSON above is the machine contract. For people, ask for SPSS-style tables:

```bash
python scripts/analyze.py --config examples/ttest-request.json --format text
python scripts/analyze.py --config examples/ttest-request.json --format markdown --plots-dir charts/
```

and for a complete deliverable, list several analyses in one request and build a report:

```bash
python scripts/spss_report.py --config examples/report-request.json --output report.html
```

`.html` output is a single self-contained file with embedded charts; `.md` writes the report plus a `<name>_figures/` folder. Add `--no-plots` to skip charts. The report ends with equivalent SPSS syntax (not executed) and the exact request used, so it can be re-run. Real output for every procedure is in [`sample-output.txt`](sample-output.txt).

## 6. Use the LLM instructions

`SKILL.md` is the core LLM instruction file. Upload or paste it into a platform’s custom-instructions/skill facility. Include `references/procedure-guide.md` if the platform cannot read companion reference files. The platform must separately support file upload and computation for end-to-end analysis; otherwise, the assistant should provide syntax/code or interpret output you provide.

## Validation and result status

Variable selections must be non-empty lists of distinct column names. Crosstab variables must be different. Numeric infinity values are rejected in requested columns (all columns for inventory), not silently treated as usable cases; explicitly correct or recode them first. No automatic recoding is performed.

Inspect `valid` before interpretation. Undefined inference (constant correlation, zero-variance differences/groups/item totals, insufficient crosstab categories) returns `valid: false`, a reason, and no usable test result. Correlation also marks invalid pairs individually. Logistic fits report convergence and are invalid when nonconvergent or separation warnings occur; numerical exceptions exit nonzero. JSON output does not by itself mean valid inference.

Audit counts are overlapping reason/variable incidences, not a disjoint partition. Do not sum exclusions to derive dropped rows. Use `rows_total - rows_used` for a procedure's unique dropped-row total; correlation instead reports each pair's N and dropped count and sets overall `rows_used` to null. ANOVA dropped-group `count` is the group's original row count; `usable_n` is its numeric, nonmissing outcome count. Describe and frequencies have per-variable missing counts rather than `data_audit`.
