# wilcoxon

## Purpose and when not
Independent paired differences, symmetry for location inference. Difference is outcome minus paired_with. Asymptotic default uses continuity correction; exact rejects zeros/tied absolute differences. All-zero differences return invalid. Difference rounding is explicit measurement precision, never automatic.
Not for clustered/weighted data or causal claims.

## Required fields and measurement
outcome and paired_with: matched scale/ordinal columns; zero_method=wilcox/pratt/zsplit; method=asymptotic/exact; optional difference_decimals=0..12. Action `wilcoxon`.

## Assumptions: evidence versus diagnostics
The user establishes design/independence and units; code checks counts, numeric coercions and degenerate inputs, not random sampling. Inspect distributions before choosing a location interpretation.

## Computation status
Helper-supported through `scripts/procedures.py`, scipy/statsmodels. No LLM arithmetic.

## Output contract
Action, N, statistic/F/odds ratio or pairwise comparisons, two-sided p or adjusted p, method, audit and limitations. Existing actions and fields remain unchanged. Text/Markdown tables and report interpretations use computed results.

## Validation
Tests cover library agreement, noisy unequal groups, ties/zeros, exact modes and invalid cases where applicable. Check N, missingness and group order. Local library agreement is not SPSS parity.

## SPSS conventions
Independent paired differences, symmetry for location inference. Difference is outcome minus paired_with. Asymptotic default uses continuity correction; exact rejects zeros/tied absolute differences. All-zero differences return invalid. Difference rounding is explicit measurement precision, never automatic.
SPSS exact/asymptotic options can differ; do not claim exact parity without fixture evidence.

## Interpretation and alternatives
Report estimates and uncertainty, distinguish distribution/location hypotheses. Choose parametric/robust/exact alternatives based on design, not a single assumption-test p.
