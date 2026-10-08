# descriptives

## Purpose and when not to use
Percentiles use pandas linear interpolation, Hyndman-Fan type 7; not SPSS Tukey hinges.
Do not use ordinary inference for clustered, survey-weighted or censored data.

## Required fields and measurement levels
variables: scale or categorical. Action/interface: `describe`.

## Assumptions: evidence versus diagnostics
User evidence must establish design, units, independence, sampling and coding. The helper cannot verify those facts. Inspect available missingness, counts, variance, convergence and sparse-cell diagnostics; unavailable diagnostics have not passed.

## Computation status
helper-supported. Run executable code; never estimate statistics with an LLM. Invalid results must not be interpreted as inference.

## Output contract
N, missing, mean, sample SD, median, quartiles, range, skew or category counts. Existing JSON keys remain stable; new keys are additive. Validity, source and software fields accompany helper requests.

## Validation
Check analysis N, exclusions, statistic/df/CI bounds and finite results against tests and a second library call where practical. Record settings and uncertainty.

## SPSS conventions
Percentiles use pandas linear interpolation, Hyndman-Fan type 7; not SPSS Tukey hinges.
SPSS-style tables are not licensed SPSS output. Compare filters, missing rules, category order, contrasts, rounding and library versions before claiming parity.

## Interpretation and alternatives
Describe estimates, direction and uncertainty, not just significance. Use design-appropriate robust/rank/exact alternatives when justified; they may target different estimands. Read `validation-and-parity.md` before claiming parity.
