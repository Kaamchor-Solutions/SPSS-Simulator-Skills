# data-preparation

## Purpose and when not to use
Never silently overwrite, impute or exclude.
Do not use ordinary inference for clustered, survey-weighted or censored data.

## Required fields and measurement levels
Approved source, target, recode/range rules and missing policy. Action/interface: `prepare`.

## Assumptions: evidence versus diagnostics
User evidence must establish design, units, independence, sampling and coding. The helper cannot verify those facts. Inspect available missingness, counts, variance, convergence and sparse-cell diagnostics; unavailable diagnostics have not passed.

## Computation status
helper-supported. Run executable code; never estimate statistics with an LLM. Invalid results must not be interpreted as inference.

## Output contract
Preserved raw columns and a transformation audit. Existing JSON keys remain stable; new keys are additive. Validity, source and software fields accompany helper requests.

## Validation
Check analysis N, exclusions, statistic/df/CI bounds and finite results against tests and a second library call where practical. Record settings and uncertainty.

## SPSS conventions
Never silently overwrite, impute or exclude.
SPSS-style tables are not licensed SPSS output. Compare filters, missing rules, category order, contrasts, rounding and library versions before claiming parity.

## Interpretation and alternatives
Describe estimates, direction and uncertainty, not just significance. Use design-appropriate robust/rank/exact alternatives when justified; they may target different estimands. Read `validation-and-parity.md` before claiming parity.

## Executable request
```json
{"action":"prepare","file":"data.csv","rules":[{"kind":"recode","source":"group","target":"group_code","values":[{"from":"control","to":0},{"from":"active","to":1}],"unmatched":"error"},{"kind":"range","source":"age","target":"age_band","ranges":[{"min":0,"max":18,"to":"child"},{"min":18,"max":130,"to":"adult"}],"unmatched":"missing"},{"kind":"dummy","source":"group","target":"group_d","levels":["control","active"],"reference":"control"}]}
```
Recode values are typed, supplied as entry lists rather than JSON object keys. Range intervals are left-closed/right-open. Overlaps, unknown levels, collisions and overwrites fail. Unmatched policies: preserve (default), missing, error. Dummy columns are target_index for each nonreference level in declared order; missing sources remain missing. Pass those named numeric columns to regression; no silent categorical encoding. Output records contain original plus derived columns, and transformations disclose matching and missing counts. Source is unchanged. Rules require analysis-owner approval before applying real-data changes.
