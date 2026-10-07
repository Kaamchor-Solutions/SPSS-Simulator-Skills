# Procedure selection reference

Use this as a decision aid, not a substitute for understanding the design. Confirm variable meaning, sampling unit, dependence, estimand, and missing-data handling before testing. Procedures below are commonly used; exact menus, defaults, and output labels vary by SPSS release and options.

## Question-to-procedure map

| Research question / design | Common procedure | Check / report |
|---|---|---|
| What does one variable look like? | Frequencies for categorical/ordinal; descriptives and distribution plots for scale | N, missing, valid %, mean/SD where meaningful, median/IQR, range; inspect unusual codes |
| Do two independent groups differ on a scale outcome? | Independent-samples t-test; consider Welch when variances differ | Group n/mean/SD, mean difference, CI, t/df/p, Hedges g or Cohen d; independence and distribution/residuals |
| Do the same participants differ twice? | Paired t-test | Matched-pair count, mean change, CI, t/df/p, paired effect size; verify pairing and difference distribution |
| Do 3+ independent groups differ on a scale outcome? | One-way ANOVA; Welch ANOVA for unequal variances | Group descriptives, F/df/p, eta-squared or omega-squared; planned/post-hoc contrasts and multiplicity |
| Are two categorical variables associated? | Pearson chi-square; Fisher exact for suitable sparse 2x2 tables | Counts and row/column percentages, chi-square/df/p, Cramér's V; expected-count warnings, sampling/design |
| Are two scale variables related linearly? | Pearson correlation; Spearman for monotonic/rank association | r or rho, CI/p, N; scatterplot, outliers, linearity, independent observations |
| Predict a scale outcome? | Linear regression (OLS); consider generalized/robust models when assumptions fail | B, SE, CI, t/p, R²/adjusted R², model F; residual diagnostics, collinearity, influence, coding/reference groups |
| Predict binary 0/1 outcome? | Binary logistic regression | B, SE, Wald/p, OR and CI, N, model fit; event coding, separation, calibration, linearity of logit for continuous predictors |
| Do multi-item scale items cohere? | Cronbach's alpha, optionally item-total / alpha-if-deleted | Number of items, complete-case N, alpha; reverse code only with key; alpha is not proof of unidimensionality or validity |

Do not select a test solely by a normality-test p-value. Graphs, sample size, design, residuals, robustness, and the scientific question all matter. For repeated measures with 3+ time points, mixed models or repeated-measures methods may be needed; do not treat rows from one person as independent. For survey weights, clusters, strata, time-to-event outcomes, count outcomes, or complex missing data, use methods that explicitly model those structures.

## Bundled companion scope

`scripts/analyze.py` currently supports: inventory, describe, frequencies, crosstab with Pearson chi-square, independent or paired t-test, one-way ANOVA, Pearson/Spearman correlation, OLS, binary logit, and Cronbach's alpha. It is a small transparent helper, not an SPSS clone. It does not implement weighting, split-file processing, complex samples, multiple imputation, robust/clustered errors, post-hoc families, exact tests, mixed models, survival analysis, or broad SPSS syntax execution. Use a validated implementation for those needs and state the implementation.

## SPSS syntax examples

Generate syntax that matches the confirmed variable names and data labels. Inspect it before sharing; syntax is a reproducibility aid, not proof of execution.

```spss
* Descriptives and histograms.
DESCRIPTIVES VARIABLES=score /STATISTICS=MEAN STDDEV MIN MAX.
FREQUENCIES VARIABLES=group /ORDER=ANALYSIS.

* Independent samples t-test (replace the group codes with the actual values).
T-TEST GROUPS=group(0 1) /VARIABLES=score /CRITERIA=CI(.95).

* Paired t-test.
T-TEST PAIRS=before WITH after (PAIRED) /CRITERIA=CI(.95).

* One-way ANOVA.
ONEWAY score BY group /STATISTICS DESCRIPTIVES HOMOGENEITY.

* Crosstab with Pearson chi-square and row percentages.
CROSSTABS /TABLES=group BY outcome /STATISTICS=CHISQ PHI /CELLS=COUNT ROW.

* Pearson correlation.
CORRELATIONS /VARIABLES=score age /PRINT=TWOTAIL /MISSING=PAIRWISE.

* Linear regression; categorical predictors need correctly specified coding.
REGRESSION /DEPENDENT=score /METHOD=ENTER age treatment.

* Binary logistic regression; confirm which outcome value is modeled as the event.
LOGISTIC REGRESSION VARIABLES=event /METHOD=ENTER age treatment.

* Internal consistency; reverse-code items first if required by the instrument key.
RELIABILITY /VARIABLES=item1 item2 item3 /MODEL=ALPHA.
```

SPSS syntax option support and command syntax can vary. If exact SPSS execution matters, have the user run syntax in their own SPSS installation and share the output or warnings for review.

## Formatted output per procedure

| Action | `--format` tables | Charts (`--plots-dir`) |
|---|---|---|
| describe | Descriptive Statistics (N, Min, Max, Mean, Std. Error, Std. Deviation, Median, quartiles, Skewness) | histogram with normal curve |
| frequencies | Statistics; Frequency / Percent / Valid Percent / Cumulative Percent | bar chart |
| crosstab | Case Processing Summary; Crosstabulation (count, % within row/column); Chi-Square Tests; Symmetric Measures | clustered bar |
| ttest (independent) | Group Statistics; Independent Samples Test (Welch row); effect size | boxplot; mean with 95% CI |
| ttest (paired) | Paired Samples Statistics; Paired Samples Test; effect size | difference histogram; scatter |
| anova | Descriptives; ANOVA (sums of squares, mean squares, F, Sig.) | boxplot; mean with 95% CI |
| correlation | Correlations matrix with Sig. (2-tailed) and N | scatter with fit line |
| regression linear | Model Summary; ANOVA; Coefficients with Beta | scatter (one predictor); residual plot |
| regression logistic | Omnibus Test; Model Summary; Classification Table; Variables in the Equation | none |
| alpha | Case Processing Summary; Reliability Statistics | none |

`scripts/spss_report.py` combines any of these into one report. Not computed (and so never shown): Levene's test, pooled-variance t row, post hoc tests, Fisher exact, collinearity statistics, Hosmer-Lemeshow.
