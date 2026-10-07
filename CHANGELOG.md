# Changelog

This project follows a simple Keep a Changelog-style format. Versions use Semantic Versioning where practical.

## [Unreleased]

### Changed
- Flattened the repository layout: all project files now live at the repository root instead of the nested `spss-simulator-opensource/` folder.
- Upgraded the README with badges, a table of contents, a repository-layout overview, a citation section, and corrected license wording.

### Added
- GitHub issue templates, a pull request template, and a CI workflow that runs the unit tests.
- `templates/analysis-report-template.md` mirroring the default report format in `SKILL.md`.
- Root `.gitignore` covering Python artifacts, generated output, and editor files.
- Repository URL and corporate author in `CITATION.cff`.

## [0.1.0] - 2026-10-08

### Added
- Portable SPSS-style LLM skill instructions and procedure guide.
- Python companion for inventory, descriptive summaries, frequencies, crosstabs, t-tests, one-way ANOVA, correlations, OLS/logistic regression, and Cronbach’s alpha.
- Getting-started, methods/limitations, contribution, security, and conduct documentation.
- Example request and fabricated demonstration data.
