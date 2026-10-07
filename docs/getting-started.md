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

Review variable names, data types, unique counts, missing values, and duplicate-row counts. Confirm that numeric category codes, special missing-value codes, dates, IDs, and value labels have been interpreted correctly. The helper does not identify user-defined missing values in `.sav` files or automatically apply SPSS value labels.

## 3. Request an analysis

Each request is UTF-8 JSON and contains the input `file`, one `action`, and action-specific fields. Paths are relative to the current working directory unless absolute. Excel can take a sheet name or index using `sheet`.

### Descriptives and frequencies

```json
{"file":"examples/demo.csv","action":"describe","variables":["score","age"]}
```

```json
{"file":"examples/demo.csv","action":"frequencies","variables":["group"]}
```

### Crosstab

```json
{"file":"examples/demo.csv","action":"crosstab","row":"group","column":"response"}
```

### Independent Welch t-test

```json
{"file":"examples/demo.csv","action":"ttest","outcome":"score","group":"arm","groups":["control","active"]}
```

`groups` is optional; if omitted, the helper uses the two observed nonmissing group values. Confirm their order, since the reported mean difference is first group minus second group.

### Paired t-test

```json
{"file":"examples/demo.csv","action":"ttest","outcome":"after","paired_with":"before"}
```

The pairwise difference is `outcome - paired_with`. Rows must represent correctly matched pairs.

### One-way ANOVA

```json
{"file":"examples/demo.csv","action":"anova","outcome":"score","group":"arm"}
```

This is classical one-way ANOVA; it does not run post-hoc tests or assess equal-variance robustness.

### Correlation

```json
{"file":"examples/demo.csv","action":"correlation","variables":["age","score"],"method":"pearson"}
```

Use `"method":"spearman"` for Spearman rank correlation. Inspect scatterplots and the study design before interpreting either result.

### Regression

```json
{"file":"examples/demo.csv","action":"regression","outcome":"score","predictors":["age","dose"],"model":"linear"}
```

```json
{"file":"examples/demo.csv","action":"regression","outcome":"event","predictors":["age","dose"],"model":"logistic"}
```

The helper requires numeric predictors. Encode categorical predictors deliberately, document the coding and reference category, and do not mistake numeric codes for continuous measurements. Logistic outcomes must be coded 0/1; the event value is 1.

### Cronbach’s alpha

```json
{"file":"examples/demo.csv","action":"alpha","variables":["item1","item2","item3"]}
```

Reverse-code items only according to the instrument’s scoring key before running this procedure. Alpha alone does not demonstrate unidimensionality or validity.

## 4. Read and preserve results

The helper writes JSON to stdout unless `--output` is specified. Keep the source dataset unchanged. All actions analyze complete observations for their requested variables; crosstabs omit incomplete pairs. Record that policy and the resulting N. The helper does not apply user-defined missing codes, filters, weights, or split-file settings.

Treat output as a calculation result, not as automatic validation of the research design. Check warnings, sample sizes, categories, assumptions, and model suitability before reporting. Refer to [`methods-and-limitations.md`](methods-and-limitations.md) for boundaries.

## 5. Use the LLM instructions

`SKILL.md` is the core LLM instruction file. Upload or paste it into a platform’s custom-instructions/skill facility. Include `references/procedure-guide.md` if the platform cannot read companion reference files. The platform must separately support file upload and computation for end-to-end analysis; otherwise, the assistant should provide syntax/code or interpret output you provide.
