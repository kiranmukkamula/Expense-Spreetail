# DECISIONS: Architectural Decision Log

This log lists the key architectural decisions made during the design and development of the Shared Expense Management Application.

---

## 1. Database Selection: PostgreSQL
- **Options Considered**: SQLite, PostgreSQL, MongoDB
- **Chosen Option**: PostgreSQL
- **Rationale**:
  - **Relational Integrity**: The database schema relies heavily on referential constraints, including cascaded deletes (`ON DELETE CASCADE`) for group deletions and restricted deletions (`ON DELETE RESTRICT`) to prevent deleting users who have outstanding ledgers.
  - **JSONB Capabilities**: Storing raw CSV row structures in `ImportRecord` requires efficient document/JSON storage. PostgreSQL's native `JSONB` type allows robust queries over staged rows.
  - **Local Setup Match**: The user has pgAdmin4 installed locally and requested verification through local PostgreSQL tools.

---

## 2. Staged CSV Import Pipeline
- **Options Considered**:
  - **Direct Import**: Parse CSV and write directly to the `Expense` and `Settlement` tables. If errors occur, rollback the transaction.
  - **Staged Imports (Chosen)**: Store uploaded CSV rows into temporary `ImportRecord` and `AnomalyRecord` tables. Run anomaly detection and return the staged data to the user for interactive UI corrections, before saving to the main ledger.
- **Rationale**:
  - Direct import does not allow interactive resolution. If a row has an unresolved payer (e.g. `Priya s` vs `Priya`), the entire file import would crash.
  - Staging allows the application to report all duplicate warnings, currency conversions, and date ambiguities in one place and let the user decide how to resolve them before writing to the database ledger.

---

## 3. Decimal and Integer Cent Storage
- **Options Considered**:
  - Storing amounts as floating-point numbers (`FLOAT`).
  - Storing amounts as high-precision decimals (`DECIMAL`).
  - Storing amounts as integer cents (`INTEGER` / `int`) (Chosen).
- **Rationale**:
  - Float types introduce rounding issues (e.g. `0.1 + 0.2 = 0.30000000000000004`).
  - While `DECIMAL` is mathematically safe, it increases calculation complexity in backend models.
  - Converting all monetary values to **integer cents** (e.g. 10.50 INR is stored as `1050`) eliminates floating-point rounding errors entirely and ensures exact mathematical balance sums. We distribute remainder cents (e.g. when splitting 100 cents among 3 people) to users sequentially so the sum of individual shares matches the total amount.

---

## 4. Debt Simplification Pathway (Greedy Min-Flow)
- **Options Considered**:
  - **Min-Flow (Greedy Algorithm)**: Match the largest creditor with the largest debtor and settle. Repeat until balances are cleared.
  - **Split-wise DFS Network Flow**: Explore all possible subsets to find the absolute minimal total transaction value.
- **Rationale**:
  - The Greedy Min-Flow algorithm reduces the total number of transactions from $O(N^2)$ to $O(N)$ effectively.
  - It is computationally lightweight, easy to verify with automated tests, and satisfies the user requirement of minimizing transaction count and showing a simplified pathway in the frontend panel.

---

## 5. Timezone Normalization
- **Options Considered**:
  - Storing all datetimes as timezone-naive UTC.
  - Storing datetimes as timezone-aware with Postgres `DateTime(timezone=True)` (Chosen).
- **Rationale**:
  - Naive datetimes complicate client-side representations since timezone offsets are lost.
  - Using UTC timezone-aware database objects ensures dates match in multiple time zones.
  - We handle SQLite test harness inconsistencies (which return naive datetimes) by implementing a normalization utility inside the testing assertions.
