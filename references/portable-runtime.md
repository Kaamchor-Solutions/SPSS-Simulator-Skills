# Portability and companion runtime

A skill is an instruction package, not a software installation. Uploading the skill to another LLM does not automatically grant file access, Excel connectors, Python, packages, SPSS, or persistent storage. The host LLM must expose file upload and/or code execution for those operations.

## Safe fallback hierarchy

1. Read the user's uploaded file with the host's available file/code tools and report exactly what was accessible.
2. If the host cannot execute analysis, ask the user to enable its code/data tool or run the provided script locally. Alternatively, generate SPSS syntax or Python/R code for the user to execute.
3. If neither uploads nor code are available, ask for a small privacy-safe excerpt, codebook, and/or SPSS output. Never claim to have processed an inaccessible workbook.

## Companion script

`../scripts/analyze.py` accepts a JSON configuration and reads CSV, TSV, Excel (`.xlsx`/`.xls` depending on installed engine), or SPSS `.sav` (requires `pyreadstat`). It writes a JSON result, with analysis summaries rather than a copied dataset. Supported actions and argument examples are embedded in `--help` and below. Install dependencies with:

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

All analyses use listwise-complete observations for the variables named in that request, except crosstabs also omit missing pairs. This helper does not infer user-defined SPSS missing-value codes, honor SPSS weights, filters, split-file settings, or value labels. The agent must surface this and verify data decisions. For regression, the initial helper accepts numeric predictors only; encode categorical predictors explicitly and document reference categories before use. Logistic outcomes must be coded 0/1. Results are not a substitute for domain review, design-aware inference, or licensed SPSS output.
