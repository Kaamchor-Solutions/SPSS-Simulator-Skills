# anova-repeated

## Purpose and when not
Pingouin one-factor rm_anova, complete-subject deletion. Duplicate subject-condition cells fail rather than average silently. At least three complete subjects. Mauchly W/chi-square/p, GG and HF epsilon, corrected dfs and scipy F p. Uncorrected generalized eta squared. No mixed design, between-subject factors, multiple within factors or multivariate tests. Sphericity automatic for two levels; undefined diagnostic is not a pass.

## Required fields and measurement
Long format: subject ID, within condition, outcome: scale; one within factor. Action `anova_repeated`.

## Assumptions: evidence versus diagnostics
User evidence establishes design, independence, units and measurement meaning. Helper checks finite inputs, complete cases, rank/count/variance constraints. Residual distributions and design assumptions are not declared passed.

## Computation status
Helper-supported in `scripts/advanced.py`. scipy/statsmodels/pingouin/sklearn compute all numeric results. No LLM arithmetic.

## Output contract
N, selected options, model-specific computed tables/diagnostics, audit, source, package versions, validity and notes. JSON addition is a new action, not a change to legacy fields. Reports display estimates from the helper.

## Validation
Noisy multi-factor/unbalanced fixtures, direct library comparisons, analytic eigenvalue/rotation identities and invalid-input tests. Published-SPSS parity is limited to fixtures named in `../tests/fixtures/parity.json`; none of these new advanced procedures currently has a licensed-SPSS comparison.

## SPSS convention notes
Pingouin one-factor rm_anova, complete-subject deletion. Duplicate subject-condition cells fail rather than average silently. At least three complete subjects. Mauchly W/chi-square/p, GG and HF epsilon, corrected dfs and scipy F p. Uncorrected generalized eta squared. No mixed design, between-subject factors, multiple within factors or multivariate tests. Sphericity automatic for two levels; undefined diagnostic is not a pass.
SPSS defaults and rotation normalization can differ. Do not claim whole-procedure parity from an omnibus-only fixture.

## Interpretation and alternatives
Explain SS/contrast or extraction/rotation policy, inspect assumptions and report uncertainty. Main effects with interactions, sphericity violations and component retention require judgment. Use mixed models/validated specialist workflows outside supported restrictions.
