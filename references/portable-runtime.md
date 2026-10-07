# Portability and companion runtime

A skill is an instruction package, not a software installation. Uploading the skill to another LLM does not automatically grant file access, Excel connectors, Python, packages, SPSS, or persistent storage. The host LLM must expose file upload and/or code execution for those operations.

## Safe fallback hierarchy

1. Read the user's uploaded file with the host's available file/code tools and report exactly what was accessible.
2. If the host cannot execute analysis, ask the user to enable its code/data tool or run the provided script locally. Alternatively, generate SPSS syntax or Python/R code for the user to execute.
3. If neither uploads nor code are available, ask for a small privacy-safe excerpt, codebook, and/or SPSS output. Never claim to have processed an inaccessible workbook.

## Companion script

`../scripts/analyze.py` accepts a JSON configuration and reads CSV, TSV, Excel (`.xlsx`/`.xls` depending on installed engine), or SPSS `.sav` (requires `pyreadstat`). It writes a JSON result, with analysis summaries rather than a copied dataset. The `--help` output describes CLI flags; supported actions and argument examples are shown below. Install dependencies with:

```bash
python -m pip install -r scripts/requirements.txt
```

Run:

```bash
python scripts/analyze.py --config request.json --output result.json
```

Minimal request:

```json
{
  "file": "study.xlsx",
  "sheet": "Data",
  "action": "describe",
  "variables": ["age", "score"]
}
```

Other examples:

```json
{"file":"study.csv","action":"frequencies","variables":["treatment"]}
{"file":"study.xlsx","action":"crosstab","row":"group","column":"response"}
{"file":"study.csv","action":"ttest","outcome":"score","group":"arm","groups":["control","active"],"paired":false}
{"file":"study.csv","action":"ttest","outcome":"post","paired_with":"pre"}
{"file":"study.csv","action":"anova","outcome":"score","group":"arm"}
{"file":"study.csv","action":"correlation","variables":["age","score"],"method":"pearson"}
{"file":"study.csv","action":"regression","outcome":"score","predictors":["age","dose"],"model":"linear"}
{"file":"study.csv","action":"regression","outcome":"event","predictors":["age","dose"],"model":"logistic"}
{"file":"study.csv","action":"alpha","variables":["item1","item2","item3"]}
{"file":"study.sav","action":"inventory"}
```

Inventory retains all rows. Describe/frequencies use per-variable nonmissing values and report missing counts. Regression/alpha are listwise, crosstabs/paired t-tests omit incomplete pairs, independent tests/ANOVA use usable outcomes within groups, and correlation is pairwise. Inferential procedures report exclusions in `data_audit`. This helper does not infer user-defined SPSS missing-value codes, honor SPSS weights, filters, split-file settings, or apply value labels (labelled `.sav` variables are read as their underlying codes). The agent must surface this and verify data decisions. For regression, the initial helper accepts numeric predictors only; encode categorical predictors explicitly and document reference categories before use. Logistic outcomes must be coded 0/1. Results are not a substitute for domain review, design-aware inference, or licensed SPSS output.

## Validation and result status

Variable selections must be non-empty lists of distinct column names. Crosstab variables must be different. Numeric infinity values are rejected in requested columns (all columns for inventory), not silently treated as usable cases; explicitly correct or recode them first. No automatic recoding is performed.

Inspect `valid` before interpretation. Undefined inference (constant correlation, zero-variance differences/groups/item totals, insufficient crosstab categories) returns `valid: false`, a reason, and no usable test result. Correlation also marks invalid pairs individually. Logistic fits report convergence and are invalid when nonconvergent or separation warnings occur; numerical exceptions exit nonzero. JSON output does not by itself mean valid inference.

Audit counts are overlapping reason/variable incidences, not a disjoint partition. Do not sum exclusions to derive dropped rows. Use `rows_total - rows_used` for a procedure's unique dropped-row total; correlation instead reports each pair's N and dropped count and sets overall `rows_used` to null. ANOVA dropped-group `count` is the group's original row count; `usable_n` is its numeric, nonmissing outcome count. Describe and frequencies have per-variable missing counts rather than `data_audit`.
