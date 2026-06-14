# AI USAGE: Interaction and Correction Log

This document lists the AI tools used, key prompts, and three concrete instances where the AI generated incorrect logic, how it was identified, and the resulting corrections.

---

## 1. AI Tools & Key Prompts
- **AI Tool**: Google Gemini (Antigravity pairs-programming agent)
- **Key Prompts Used**:
  - *"How do we handle timezone offset discrepancies between SQLAlchemy DateTime objects and parsed naive datetimes in Python?"*
  - *"Design a min-flow debt simplification algorithm that takes a dictionary of net group member balances in integer cents and returns a list of minimal transactions."*
  - *"Create a staged import table model to hold raw CSV rows and scan them for duplicates, inactive members, and currency convertibility."*

---

## 2. Failure Cases, Identification, and Solutions

### Case 1: Timezone Comparison Crash in Integration Tests
- **AI's Action**: The AI generated database comparisons directly comparing SQL datetime fields:
  ```python
  if payer_membership.joined_at > expense_date:
  ```
- **How It Failed**:
  - PostgreSQL returns timezone-aware datetime objects, whereas the SQLite in-memory engine (used for unit tests) returns timezone-naive datetime objects even if `DateTime(timezone=True)` is used.
  - This mismatch caused `TypeError: can't compare offset-naive and offset-aware datetimes` in tests.
- **How We Caught It**:
  - Running automated backend test suites (`pytest`) triggered test failures with offset-naive error logs.
- **The Correction**:
  - Implemented a normalization helper that checks for `tzinfo` and strips/replaces it during comparisons:
    ```python
    payer_joined_naive = payer_mem.joined_at.replace(tzinfo=None) if payer_mem.joined_at.tzinfo else payer_mem.joined_at
    expense_date_naive = expense_date.replace(tzinfo=None) if expense_date.tzinfo else expense_date
    if payer_joined_naive > expense_date_naive:
    ```

---

### Case 2: Payer Resolution Dropdown Hidden in UI for Missing Payers
- **AI's Action**: The AI generated a conditional render check in `App.jsx` for showing the payer resolution dropdown:
  ```javascript
  {rec.anomalies.some(a => a.anomaly_type === "UNRESOLVED_PAYER") && ( ... )
  ```
- **How It Failed**:
  - If the CSV row had a completely empty `paid_by` column, the anomaly type was `MISSING_PAYER` (instead of `UNRESOLVED_PAYER`).
  - As a result, the dropdown select was hidden in the UI, leaving the user with a critical anomaly block and no way to map the payer before clicking import.
- **How We Caught It**:
  - Code walkthrough and user UI analysis revealed the missing mapping box for empty columns.
- **The Correction**:
  - Expanded the conditional statement to include both anomaly types:
    ```javascript
    {rec.anomalies.some(a => a.anomaly_type === "UNRESOLVED_PAYER" || a.anomaly_type === "MISSING_PAYER") && ( ... )
    ```

---

### Case 3: Empty User Creation in CSV Import Approval
- **AI's Action**: The AI wrote the following user resolution logic in `imports.py`:
  ```python
  payer_user = get_or_create_user(paid_by_str)
  ```
- **How It Failed**:
  - If a row's `paid_by` field was empty `""`, `get_or_create_user("")` was called.
  - This function created a database user with an empty name `""` and email `@split.local`. This caused blank name entries (`Dev -> `) in the Debt Simplification panel.
- **How We Caught It**:
  - Inspected the database using a custom python script (`db.query(User).all()`) and found the empty user ID `04627010-5115-4f03-8485-10e1c68e1398` with name `""` and email `@split.local`.
- **The Correction**:
  - Added a fallback safety check inside `get_or_create_user` to return an `"Unknown Payer"` account (email `unknown@split.local`) if the name string is empty/whitespace.
  - Added a validation rule in the `/approve` endpoint raising an HTTP 400 exception if `paid_by` is empty and no mapping is provided.
  - Added test case `test_csv_approval_validation_errors` verifying this protection.
