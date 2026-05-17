# Oraclaire — Burnout Risk Assessment

<p align="center">
  <strong>Early detection. Plain language. Privacy-first.</strong>
</p>

Oraclaire is a weekly burnout risk assessment tool that helps employees, managers, and HR teams identify and respond to burnout risk before it becomes a crisis. It uses a Random Forest classifier with SHAP-based explainability to give each employee a personalised risk tier, explain what's driving it, and suggest relevant resources.

---

## Who it's for

| Role         | What they see                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------ |
| **Employee** | Own risk tier, what factors are contributing, and suggested resources. Individual answers are private. |
| **Manager**  | Team-level trends and ORT (Organisational Risk Threshold). No individual scores.                       |
| **HR Admin** | Org-wide aggregates, participation rates, and a reviewer queue for Critical-tier employees.            |

---

## How it works

**The weekly check-in** asks five plain-language questions covering the main burnout drivers:

1. Workload — how busy you've been and whether it's sustainable
2. Energy — whether your energy levels have been holding up
3. Recovery — how well you've been switching off outside work
4. Pressure signals — signs you were being stretched too far
5. Support — whether you had the resources and backing you needed

Each answer maps to a burnout risk factor. The model produces a risk tier:

| Tier         | What it means                                       |
| ------------ | --------------------------------------------------- |
| **Low**      | You're doing well.                                  |
| **Moderate** | Some areas worth watching.                          |
| **High**     | Support is available, please consider reaching out. |
| **Critical** | Please talk to someone.                             |

**Privacy by design** — individual answers are only ever visible to the employee who gave them. Managers see team-level patterns only. HR sees org-wide aggregates with exclusions applied (e.g. employees on leave are not counted).

---

## Running locally

```bash
# Install dependencies
uv sync

# Train the model (first run only)
uv run python -m src.model.train

# Start the app
uv run streamlit run src/app.py
```

Open `http://localhost:8501`. Select a role and enter any employee ID to explore the demo.

---

## Architecture

```
src/
├── app.py              # Streamlit entry point, role routing, sidebar
├── config.py           # Thresholds, tier boundaries, feature labels, resources
├── model/
│   ├── train.py        # Random Forest training + SHAP explainer
│   └── serve.py        # Inference + SHAP decomposition
└── views/
    ├── employee_ux.py  # 7-screen employee flow (intro → check-in → result → radar → factors → resources → trend)
    ├── employee.py     # Employee dashboard
    ├── manager.py      # Manager team view
    ├── hr_aggregate.py # HR org-wide view
    └── reviewer.py     # Critical-tier reviewer queue
```

**Key thresholds** (`src/config.py`):

- `THRESHOLD_A = 0.35` — general population
- `THRESHOLD_B = 0.30` — senior tier (higher false-negative cost)
- `ORT_CEILING = 0.20` — team ORT triggers review at 20% High+Critical

---

## For developers

- All threshold values are in `src/config.py` — update there, no code changes needed elsewhere.
- The model is a Random Forest (`n_estimators=100, max_depth=5`) trained on HR-validated burnout labels.
- SHAP decomposes each prediction into per-factor contributions so the app can explain _why_ someone is at risk in plain language.
- The 5-question check-in is defined as a data structure in `employee_ux.py` (`ASSESSMENT_QUESTIONS`) — questions and options can be changed without touching model code.
- Demo mode runs entirely locally with no backend. Authenticated mode connects to an Oraclaire backend API.

---

## Target audiences

- **Business manager approving the app** — sidebar explains ORT thresholds, what patterns to watch for, and what you can/cannot see.
- **Employee using the app** — intro screen sets expectations before the check-in; privacy promise is visible on every result screen.
- **Developer inheriting the codebase** — sidebar (HR Admin view) points to `src/config.py` for all thresholds, `src/model/` for methodology, and `src/views/` for the UX screens.
