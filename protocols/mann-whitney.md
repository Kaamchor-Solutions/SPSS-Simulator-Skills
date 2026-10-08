# mann-whitney

## Purpose and when not
Independent observations supplied by the user. Similar distribution shapes are needed to interpret a location difference. Asymptotic scipy U uses tie correction and continuity correction; exact rejects ties. U is for the first group.
Not for clustered/weighted data or causal claims.

## Required fields and measurement
outcome: scale/ordinal; group: nominal; exactly two typed groups; method=asymptotic (default) or exact. Action `mann_whitney`.

## Assumptions: evidence versus diagnostics
The user establishes design/independence and units; code checks counts, numeric coercions and degenerate inputs, not random sampling. Inspect distributions before choosing a location interpretation.

## Computation status
Helper-supported through `scripts/procedures.py`, scipy/statsmodels. No LLM arithmetic.

## Output contract
Action, N, statistic/F/odds ratio or pairwise comparisons, two-sided p or adjusted p, method, audit and limitations. Existing actions and fields remain unchanged. Text/Markdown tables and report interpretations use computed results.

## Validation
Tests cover library agreement, noisy unequal groups, ties/zeros, exact modes and invalid cases where applicable. Check N, missingness and group order. Local library agreement is not SPSS parity.

## SPSS conventions
Independent observations supplied by the user. Similar distribution shapes are needed to interpret a location difference. Asymptotic scipy U uses tie correction and continuity correction; exact rejects ties. U is for the first group.
SPSS exact/asymptotic options can differ; do not claim exact parity without fixture evidence.

## Interpretation and alternatives
Report estimates and uncertainty, distinguish distribution/location hypotheses. Choose parametric/robust/exact alternatives based on design, not a single assumption-test p.
