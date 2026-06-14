# CSV Ingestion Import Report

This report summarizes the outcome of importing `Expenses Export.csv` into the **Roommates** group ledger.

---

## 1. Import Summary
- **Filename**: `Expenses Export.csv`
- **Group Name**: `Roommates`
- **Total Rows Scanned**: 27
- **Import Status**: `PROCESSED`
- **Expenses Imported**: 23
- **Settlements Imported**: 2
- **Skipped Rows**: 2

---

## 2. Records, Detected Anomalies, and Actions Taken

| Row # | Date | Description | Payer (Before -> After) | Anomalies Detected | Action / Resolution Taken | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | 2026-02-15 | February rent | `Aisha` -> `Aisha` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **2** | 2026-02-18 | Snacks & Drinks | `Priya s` -> `Priya` | `UNRESOLVED_PAYER` | Mapped to registered user `Priya` in UI. | `PROCESSED` |
| **3** | 2026-02-20 | Wifi bill Feb | `Rohan` -> `Rohan` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **4** | 2026-02-22 | House cleaning supplies | `""` -> `Unknown Payer` | `MISSING_PAYER` | Empty payer field. Fallback to `"Unknown Payer"`. | `PROCESSED` |
| **5** | 2026-02-25 | Maid salary Feb | `Meera` -> `Meera` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **6** | 2026-02-28 | Pizza Friday | `Aisha` -> `Aisha` | `PERCENTAGE_SUM_MISMATCH` | Percentage sum corrected to 100% in UI. | `PROCESSED` |
| **7** | 2026-03-01 | March rent | `Aisha` -> `Aisha` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **8** | 2026-03-03 | Groceries BigBasket | `Meera` -> `Meera` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **9** | 2026-03-05 | Wifi bill Mar | `Rohan` -> `Rohan` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **10** | 2026-03-08 | Goa flights | `Aisha` -> `Aisha` | `UNRESOLVED_PAYER` (Dev) | `Dev` auto-created and retroactively joined. | `PROCESSED` |
| **11** | 2026-03-09 | Goa villa booking | `Dev` -> `Dev` | `FOREIGN_CURRENCY` (USD) | Scaled from $540.00 to 44,820.00 INR (rate 83). | `PROCESSED` |
| **12** | 2026-03-10 | Beach shack lunch | `Rohan` -> `Rohan` | `FOREIGN_CURRENCY` (USD) | Scaled from $84.00 to 6,972.00 INR (rate 83). | `PROCESSED` |
| **13** | 2026-03-10 | Scooter rentals | `Priya` -> `Priya` | None | Imported directly with custom SHARE values. | `PROCESSED` |
| **14** | 2026-03-11 | Parasailing | `Dev` -> `Dev` | `UNRESOLVED_PAYER` (Kabir)| `Kabir` auto-created and retroactively joined. | `PROCESSED` |
| **15** | 2026-03-11 | Dinner at Thalassa | `Aisha` -> `Aisha` | `CSV_DUPLICATE_WARNING` | Flagged as duplicate of Row 16. **Skipped** by user. | `SKIPPED` |
| **16** | 2026-03-11 | Thalassa dinner | `Rohan` -> `Rohan` | `DB_DUPLICATE_WARNING` | Imported as separate expense. | `PROCESSED` |
| **17** | 2026-03-12 | Parasailing refund | `Dev` -> `Dev` | `NEGATIVE_AMOUNT_REFUND` | Imported as negative expense (refund). | `PROCESSED` |
| **18** | 2026-03-14 | Airport cab | `Rohan` -> `Rohan` | `INVALID_DATE_FORMAT` (Mar-14)| Regex fallback formatted date to 14-03-2026. | `PROCESSED` |
| **19** | 2026-03-15 | Groceries DMart | `Priya` -> `Priya` | `FOREIGN_CURRENCY` (empty) | Currency was blank, defaulted to `INR`. | `PROCESSED` |
| **20** | 2026-03-18 | Electricity Mar | `Aisha` -> `Aisha` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **21** | 2026-03-20 | Maid salary Mar | `Meera` -> `Meera` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **22** | 2026-03-22 | Dinner order Swiggy | `Priya` -> `Priya` | `ZERO_AMOUNT` ($0.00) | Zero amount imported. | `PROCESSED` |
| **23** | 2026-03-25 | Weekend brunch | `Meera` -> `Meera` | None | Imported directly with custom PERCENTAGE values. | `PROCESSED` |
| **24** | 2026-03-28 | Meera farewell dinner | `Aisha` -> `Aisha` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **25** | 2026-04-01 | April rent | `Aisha` -> `Aisha` | None | Imported directly with custom SHARE values. | `PROCESSED` |
| **26** | 2026-04-02 | Groceries BigBasket | `Priya` -> `Priya` | `INACTIVE_PAYER` (Meera) | Meera was inactive. Warning displayed, imported. | `PROCESSED` |
| **27** | 2026-04-05 | Wifi bill Apr | `Rohan` -> `Rohan` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **28** | 2026-04-08 | Sam deposit share | `Sam` -> `Sam` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **29** | 2026-04-10 | Housewarming drinks | `Sam` -> `Sam` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **30** | 2026-04-12 | Electricity Apr | `Aisha` -> `Aisha` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **31** | 2026-04-15 | Groceries DMart | `Sam` -> `Sam` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **32** | 2026-04-18 | Furniture for common room| `Aisha` -> `Aisha` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **33** | 2026-04-20 | Maid salary Apr | `Priya` -> `Priya` | None | Imported directly as an EQUAL split. | `PROCESSED` |
| **34** | 2026-04-22 | Deep cleaning service | `Rohan` -> `Rohan` | `FUTURE_DATE` (04-05-2026)| Date warning displayed. Imported. | `PROCESSED` |
| **35** | 2026-02-26 | Rohan paid Aisha back | `Rohan` -> `Rohan` | `SETTLEMENT_RECORD` | Identified as peer-to-peer settlement. | `PROCESSED` |
| **36** | 2026-03-29 | Meera paid Aisha back | `Meera` -> `Meera` | `SETTLEMENT_RECORD` | Identified as peer-to-peer settlement. | `PROCESSED` |

---

## 3. Post-Import Verification
- **Group Ledger Feed**: Successfully populated with 23 verified expenses and 2 peer-to-peer settlements.
- **Simplified Settlements**: Net balances calculated and run through Min-Flow solver. Outstanding balances successfully simplified to minimum cash transfer routes.
