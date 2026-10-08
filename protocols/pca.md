# pca

## Purpose and when not
Principal components extraction using sklearn full SVD, not common-factor analysis. Correlation uses sample-SD scaling. Orthogonal varimax via statsmodels without Kaiser normalization. Retention count explicit; eigenvalues and variance ratios are pre-rotation. Loading signs normalized for display only. No oblique rotation, scores, automatic retention, KMO/Bartlett or factor-analysis claim.

## Required fields and measurement
variables: scale list; n_components=1..min(N-1,p); scale=correlation/covariance; rotation=none/varimax. Action `pca`.

## Assumptions: evidence versus diagnostics
User evidence establishes design, independence, units and measurement meaning. Helper checks finite inputs, complete cases, rank/count/variance constraints. Residual distributions and design assumptions are not declared passed.

## Computation status
Helper-supported in `scripts/advanced.py`. scipy/statsmodels/pingouin/sklearn compute all numeric results. No LLM arithmetic.

## Output contract
N, selected options, model-specific computed tables/diagnostics, audit, source, package versions, validity and notes. JSON addition is a new action, not a change to legacy fields. Reports display estimates from the helper.

## Validation
Noisy multi-factor/unbalanced fixtures, direct library comparisons, analytic eigenvalue/rotation identities and invalid-input tests. Published-SPSS parity is limited to fixtures named in `../tests/fixtures/parity.json`; none of these new advanced procedures currently has a licensed-SPSS comparison.

## SPSS convention notes
Principal components extraction using sklearn full SVD, not common-factor analysis. Correlation uses sample-SD scaling. Orthogonal varimax via statsmodels without Kaiser normalization. Retention count explicit; eigenvalues and variance ratios are pre-rotation. Loading signs normalized for display only. No oblique rotation, scores, automatic retention, KMO/Bartlett or factor-analysis claim.
SPSS defaults and rotation normalization can differ. Do not claim whole-procedure parity from an omnibus-only fixture.

## Interpretation and alternatives
Explain SS/contrast or extraction/rotation policy, inspect assumptions and report uncertainty. Main effects with interactions, sphericity violations and component retention require judgment. Use mixed models/validated specialist workflows outside supported restrictions.
