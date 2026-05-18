# Phase 10 — Streamlit Login UI Fix & Codify

## What

Fixed critical login routing bug: Manager/HR Admin logins were routing to employee survey instead of their respective dashboards.

## Root Causes

1. **Missing `st.rerun()`**: Form submission set `session_state` but Streamlit needed `rerun()` to re-render with new state
2. **Missing `return` after rerun**: Execution fell through to `page_employee()` on same render before rerun fired
3. **`st.html()` strips `name` attributes**: Native HTML forms inside `st.html()` don't capture `st.selectbox()` values — need `st.form()` instead

## Fix

- Added `st.rerun()` after setting query params in login handler
- Added `return` after rerun to prevent fallthrough
- Migrated login form from `st.html()` HTML form to `st.form()` with `st.selectbox()`

## Verified Routes

| Role         | Destination     |
| ------------ | --------------- |
| manager      | Team Dashboard  |
| hr_admin     | Org Overview    |
| system_admin | Org Overview    |
| employee     | Weekly Check-in |

## Codified

Added Section 12 to `.claude/agents/project/oraclaire-product-knowledge.md`:

- `st.form()` pattern (vs `st.html()`)
- `return` after `st.rerun()`
- Role routing table
- CSS `pointer-events: none` for decorative HTML panels
- Split-screen layout CSS technique

## Commit

`dfa1014` — fix(login): use st.form() for reliable role submission and clean split-screen layout
