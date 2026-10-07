# Methods and limitations

## Design principle

Keep the LLM in an analyst/orchestration role and delegate numeric computation to executable statistical code. Treat every inferred data meaning as tentative; preserve source data; make filters, recodes, exclusions, missing-data policies, test choices, and event coding explicit. Do not invent analyses when computation or source access is unavailable.

## Current helper procedures

| Action | Implemented calculation | Important boundaries |
|---|---|---|
| `inventory` | Rows, columns, duplicate rows, type, unique and missing counts, small set of sample values | Does not reveal full codebook, SPSS metadata, or user-defined missing values |
| `describe` | Numeric N, missing N, mean, sample SD, median, quartiles, min/max, skew; categorical counts/valid percentages | Classification is heuristic; verify measurement level |
| `frequencies` | Counts and valid percentages | Does not infer ordered category meaning or labels |
| `crosstab` | Counts, row/column percentages, Pearson chi-square, expected-cell counts, Cramér’s V | Uses asymptotic Pearson chi-square, not Fisher exact; account for sparse cells and sampling design |
| `ttest` independent | Welch two-sample t-test, group summaries, mean difference, CI, descriptive pooled-SD Cohen’s d | Independent observations; no robust bootstrap, equivalence test, or multiple-comparison correction |
| `ttest` paired | Paired t-test, mean paired change and CI, Cohen’s dz | Requires valid one-to-one pairing and a defensible distribution of paired differences |
| `anova` | Classical one-way F test, group summaries, eta-squared | No Welch ANOVA, post-hoc test, planned contrasts, or assumption diagnostic |
| `correlation` | Pairwise Pearson or Spearman coefficient and p-value | No confidence interval, partial correlation, multiplicity adjustment, or missingness model |
| `regression` linear | OLS coefficients, classical SE/CI/p, model F, R² and adjusted R² | Numeric predictors only; no categorical factor expansion, robust/clustered errors, diagnostics, weights, or imputation |
| `regression` logistic | Binary logit, coefficients, OR/CI, Wald p, McFadden pseudo-R² and LR p | Numeric predictors only; event must be 1; separation/calibration and model specification need review |
| `alpha` | Cronbach’s alpha on listwise-complete numeric item rows | Reverse-keying is not automatic; no item-total/alpha-if-deleted output or validity claim |

## Shared behavior

- `.csv`, `.tsv`, `.xlsx`/`.xls` (subject to available pandas engine), and `.sav` (requires `pyreadstat`) are supported.
- Analyses use listwise-complete cases for requested variables. Crosstabs omit incomplete pairs.
- No automatic missing-code replacement, weighting, filtering, case exclusion, outlier deletion, recoding, imputation, or category encoding occurs.
- The helper reports summaries/results as JSON. It does not send files to an external service.
- A successful numerical calculation does not establish that the chosen procedure is appropriate.

## Statistical interpretation

Review independence, sampling design, outcome/predictor measurement, functional form, residual behavior, influential cases, sparse tables, model convergence/separation, and the intended estimand. Normality-test p-values alone should not dictate procedure choice. Treat p-values as one component of evidence, report effect sizes and uncertainty, and disclose multiple-testing decisions. Association does not establish causation.

For complex survey designs, clustered/repeated observations, survival/time-to-event, count outcomes, robust inference, multiple imputation, equivalence/non-inferiority, Bayesian analysis, or advanced post-hoc procedures, use suitable validated software and explicitly name it. Do not use this helper as if those features were implemented.

## SPSS comparison

This is not an IBM SPSS engine and does not read every SPSS setting. Results may differ because of software versions, default options, user-missing definitions, value labels, weights, filters, split-file state, variance corrections, coding, rounding, or the selected estimator. To match a specific SPSS analysis, document the exact version, syntax, options, and data transformations, then compare with output from that SPSS installation.

## Data protection

Use de-identified or minimum-necessary data. Keep private datasets and analysis outputs out of the source repository. Do not send data to third-party LLM platforms without authorization and an appropriate privacy review. Follow institutional, contractual, and jurisdictional data-protection requirements.
