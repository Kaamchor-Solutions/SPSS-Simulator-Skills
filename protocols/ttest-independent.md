# ttest-independent

## Purpose and when not to use
Typed group labels must match observed storage values. Independent design is user evidence.
Do not use ordinary inference for clustered, survey-weighted or censored data.

## Required fields and measurement levels
outcome: scale; group: nominal; groups: two typed labels. Action/interface: `ttest`.

## Assumptions: evidence versus diagnostics
User evidence must establish design, units, independence, sampling and coding. The helper cannot verify those facts. Inspect available missingness, counts, variance, convergence and sparse-cell diagnostics; unavailable diagnostics have not passed.

## Computation status
helper-supported. Run executable code; never estimate statistics with an LLM. Invalid results must not be interpreted as inference.

## Output contract
Welch t, df, two-sided p, first-minus-second difference, CI and descriptive pooled-SD d. Existing JSON keys remain stable; new keys are additive. Validity, source and software fields accompany helper requests.

## Validation
Check analysis N, exclusions, statistic/df/CI bounds and finite results against tests and a second library call where practical. Record settings and uncertainty.

## SPSS conventions
Typed group labels must match observed storage values. Independent design is user evidence.
SPSS-style tables are not licensed SPSS output. Compare filters, missing rules, category order, contrasts, rounding and library versions before claiming parity.

## Interpretation and alternatives
Describe estimates, direction and uncertainty, not just significance. Use design-appropriate robust/rank/exact alternatives when justified; they may target different estimands. Read `validation-and-parity.md` before claiming parity.

## Additional output
`pooled_variance` contains t, df, p, SE and CI computed by statsmodels CompareMeans. `levene` contains mean-centered scipy F, df1, df2, p and validity. Both variance rows are displayed; legacy Welch keys are unchanged.
