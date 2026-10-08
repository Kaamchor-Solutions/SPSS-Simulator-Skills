# reporting

## Purpose and when not to use
No handwritten numeric results. Generated syntax is not executed SPSS output.
Do not use ordinary inference for clustered, survey-weighted or censored data.

## Required fields and measurement levels
file, analyses, title; output .md or .html. Action/interface: `scripts/spss_report.py`.

## Assumptions: evidence versus diagnostics
User evidence must establish design, units, independence, sampling and coding. The helper cannot verify those facts. Inspect available missingness, counts, variance, convergence and sparse-cell diagnostics; unavailable diagnostics have not passed.

## Computation status
helper-supported. Run executable code; never estimate statistics with an LLM. Invalid results must not be interpreted as inference.

## Output contract
Computed tables, interpretation, diagnostics, reproducibility and explicit failed analyses. Requests and package versions are included. Equivalent SPSS syntax is supplied only for legacy procedures; new procedures use the executable request/code for reproduction, not unverified SPSS syntax.

## Validation
Check analysis N, exclusions, statistic/df/CI bounds and finite results against tests and a second library call where practical. Record settings and uncertainty.

## SPSS conventions
No handwritten numeric results. Generated syntax is not executed SPSS output.
SPSS-style tables are not licensed SPSS output. Compare filters, missing rules, category order, contrasts, rounding and library versions before claiming parity.

## Interpretation and alternatives
Describe estimates, direction and uncertainty, not just significance. Use design-appropriate robust/rank/exact alternatives when justified; they may target different estimands. Read `validation-and-parity.md` before claiming parity.
