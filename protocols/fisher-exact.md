# fisher-exact

## Purpose and when not
Independent units; complete-case 2x2 table, sorted category order. scipy two-sided probability-ordering conditional test. Sample odds ratio, not conditional MLE. Infinite odds ratios serialize as null; exact p remains usable. No odds-ratio CI.
Not for clustered/weighted data or causal claims.

## Required fields and measurement
row and column: each exactly two observed categorical levels. Action `fisher_exact`.

## Assumptions: evidence versus diagnostics
The user establishes design/independence and units; code checks counts, numeric coercions and degenerate inputs, not random sampling. Inspect distributions before choosing a location interpretation.

## Computation status
Helper-supported through `scripts/procedures.py`, scipy/statsmodels. No LLM arithmetic.

## Output contract
Action, N, statistic/F/odds ratio or pairwise comparisons, two-sided p or adjusted p, method, audit and limitations. Existing actions and fields remain unchanged. Text/Markdown tables and report interpretations use computed results.

## Validation
Tests cover library agreement, noisy unequal groups, ties/zeros, exact modes and invalid cases where applicable. Check N, missingness and group order. Local library agreement is not SPSS parity.

## SPSS conventions
Independent units; complete-case 2x2 table, sorted category order. scipy two-sided probability-ordering conditional test. Sample odds ratio, not conditional MLE. Infinite odds ratios serialize as null; exact p remains usable. No odds-ratio CI.
SPSS exact/asymptotic options can differ; do not claim exact parity without fixture evidence.

## Interpretation and alternatives
Report estimates and uncertainty, distinguish distribution/location hypotheses. Choose parametric/robust/exact alternatives based on design, not a single assumption-test p.
