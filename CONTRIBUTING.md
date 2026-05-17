# Contributing to Oraclaire

We welcome contributions to Oraclaire. This document provides guidelines for contributing.

## About This Repository

Oraclaire is a workplace burnout risk assessment tool — it helps employees, managers, and HR teams identify burnout risk early using a Random Forest classifier with SHAP-based explainability.

## Getting Started

```bash
# Install dependencies
uv sync

# Train the model (first run only)
uv run python -m src.model.train

# Start the app
uv run streamlit run src/app.py
```

Open `http://localhost:8501` to use the app.

## What to Contribute

- **Bug fixes**: Check existing issues before opening new ones
- **Model improvements**: Retraining, feature engineering, threshold tuning
- **UX screens**: New views or modifications to employee/manager/HR flows
- **Integrations**: HRIS connectors (BambooHR, Workday)

## Guidelines

### Code Standards

- All threshold values live in `src/config.py` — no hardcoded magic numbers
- The 5-question check-in is defined in `src/views/employee_ux.py` (`ASSESSMENT_QUESTIONS`) — questions can be changed without touching model code
- Demo mode runs entirely locally with no backend

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org):

```
feat(model): improve risk tier thresholds
fix(ux): correct blank result screen on Manager view
docs: update deployment checklist
```

## Pull Request Process

1. Ensure tests pass: `uv run pytest`
2. Verify Streamlit runs: `uv run streamlit run src/app.py`
3. Request review from maintainers

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
