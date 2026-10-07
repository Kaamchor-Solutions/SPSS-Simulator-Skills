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
- Regression and alpha use listwise-complete cases for requested variables; describe and frequencies use per-variable nonmissing values, not listwise deletion. Crosstabs and paired t-tests omit incomplete pairs, and correlation is computed pairwise per variable pair (per-pair N is reported).
- Inferential procedures (t-tests, ANOVA, correlation, regression, alpha and crosstabs) carry a `data_audit` object (`rows_total`, `rows_used`, `exclusions` with reasons and counts). Treat a non-empty `exclusions` list as a warning and check it before relying on the analysis N.
- SPSS `.sav` value labels are not applied; labelled variables are read as their underlying codes. User-defined SPSS missing values are not identified.
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

## Validation and result status

Variable selections must be non-empty lists of distinct column names. Crosstab variables must be different. Numeric infinity values are rejected in requested columns (all columns for inventory), not silently treated as usable cases; explicitly correct or recode them first. No automatic recoding is performed.

Inspect `valid` before interpretation. Undefined inference (constant correlation, zero-variance differences/groups/item totals, insufficient crosstab categories) returns `valid: false`, a reason, and no usable test result. Correlation also marks invalid pairs individually. Logistic fits report convergence and are invalid when nonconvergent or separation warnings occur; numerical exceptions exit nonzero. JSON output does not by itself mean valid inference.

Audit counts are overlapping reason/variable incidences, not a disjoint partition. Do not sum exclusions to derive dropped rows. Use `rows_total - rows_used` for a procedure's unique dropped-row total; correlation instead reports each pair's N and dropped count and sets overall `rows_used` to null. ANOVA dropped-group `count` is the group's original row count; `usable_n` is its numeric, nonmissing outcome count. Describe and frequencies have per-variable missing counts rather than `data_audit`.

## Formatted output scope

The tables imitate SPSS layout and naming, not every SPSS option. Not computed: Levene's test and the pooled-variance t row, post hoc tests, Fisher exact and likelihood-ratio chi-square rows, collinearity and Durbin-Watson statistics, Hosmer-Lemeshow. Percentiles use linear interpolation (SPSS defaults to weighted average), so quartiles can differ slightly. ANOVA sums of squares, the regression ANOVA table, Wald statistics and standard errors of differences are exact arithmetic on the computed results. Report interpretation text is generated from the numbers and is deliberately association-only; review it against the study design.
