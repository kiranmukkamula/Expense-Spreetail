from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import re
from decimal import Decimal

class AnomalyResult:
    def __init__(
        self,
        anomaly_type: str,
        severity: str,  # INFO, WARNING, CRITICAL
        description: str,
        suggested_action: str,
        approval_required: bool = True
    ):
        self.anomaly_type = anomaly_type
        self.severity = severity
        self.description = description
        self.suggested_action = suggested_action
        self.approval_required = approval_required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "suggested_action": self.suggested_action,
            "approval_required": self.approval_required
        }

class AnomalyRule(ABC):
    @abstractmethod
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        """
        Runs anomaly checks on the parsed CSV row.
        context keys:
          - group_members: List of dicts representing group members (id, name, email, joined_at, left_at)
          - existing_expenses: List of existing Expense objects in the DB
          - uploaded_rows: List of all parsed rows in the current CSV batch
          - row_index: Current row number (int)
        """
        pass

# ----------------- Core Rules -----------------

class MissingPayerRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        payer = str(row_data.get("paid_by") or "").strip()
        if not payer:
            return AnomalyResult(
                anomaly_type="MISSING_PAYER",
                severity="CRITICAL",
                description="The payer field is empty.",
                suggested_action="Specify a valid member of the group.",
                approval_required=True
            )
        return None

class InactiveMemberRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        payer = str(row_data.get("paid_by") or "").strip().lower()
        if not payer:
            return None
            
        group_members = context.get("group_members", [])
        expense_date = context.get("parsed_date")
        
        # Helper to match name/email case insensitively
        def get_member(name_or_email: str):
            for m in group_members:
                if m["name"].lower() == name_or_email or m["email"].lower() == name_or_email:
                    return m
            return None

        # Check payer
        payer_member = get_member(payer)
        if not payer_member:
            return AnomalyResult(
                anomaly_type="UNRESOLVED_PAYER",
                severity="CRITICAL",
                description=f"Payer '{row_data.get('paid_by')}' is not registered in this group.",
                suggested_action="Invite user to group or map to an existing group member.",
                approval_required=True
            )

        # If we have a parsed date, check if they were active on this date
        if expense_date and payer_member:
            joined = payer_member.get("joined_at")
            left = payer_member.get("left_at")
            
            # Normalize to naive for comparison to support SQLite vs Postgres timezone parsing
            exp_date_naive = expense_date.replace(tzinfo=None) if expense_date.tzinfo else expense_date
            joined_naive = joined.replace(tzinfo=None) if (joined and joined.tzinfo) else joined
            left_naive = left.replace(tzinfo=None) if (left and left.tzinfo) else left
            
            if (joined_naive and exp_date_naive < joined_naive) or (left_naive and exp_date_naive >= left_naive):
                return AnomalyResult(
                    anomaly_type="INACTIVE_PAYER",
                    severity="WARNING",
                    description=f"Payer '{payer_member['name']}' was inactive in the group on the transaction date {expense_date.strftime('%Y-%m-%d')}.",
                    suggested_action="Re-activate membership or adjust expense date.",
                    approval_required=True
                )
        return None

class DuplicateExpenseRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        desc = str(row_data.get("description") or "").strip().lower()
        amount = row_data.get("parsed_amount")
        expense_date = context.get("parsed_date")
        row_idx = context.get("row_index", -1)
        
        if not desc or amount is None or not expense_date:
            return None

        # 1. Check duplicate within current CSV batch
        uploaded_rows = context.get("uploaded_rows", [])
        for other_idx, other in enumerate(uploaded_rows):
            if other_idx == row_idx:
                continue
            other_desc = str(other.get("description") or "").strip().lower()
            other_amount = other.get("parsed_amount")
            # approximate matching for date or identical date
            other_date_str = other.get("date")
            
            # If descriptions are very similar and amounts are identical on the same date
            if other_amount == amount and (desc in other_desc or other_desc in desc):
                # We only flag on the later row
                if row_idx > other_idx:
                    return AnomalyResult(
                        anomaly_type="CSV_DUPLICATE_WARNING",
                        severity="WARNING",
                        description=f"Row {row_idx + 1} appears to be a duplicate of Row {other_idx + 1} in this file ('{row_data.get('description')}' vs '{other.get('description')}').",
                        suggested_action="Skip importing this row or approve if they are indeed separate expenses.",
                        approval_required=True
                    )

        # 2. Check duplicate with existing DB expenses
        existing_expenses = context.get("existing_expenses", [])
        for exp in existing_expenses:
            # Check same day and identical amount
            if exp.amount == amount and exp.expense_date.date() == expense_date.date():
                if desc in exp.description.lower() or exp.description.lower() in desc:
                    return AnomalyResult(
                        anomaly_type="DB_DUPLICATE_WARNING",
                        severity="WARNING",
                        description=f"This expense looks similar to an existing expense in database: '{exp.description}' paid by {exp.payer.name} on {exp.expense_date.strftime('%Y-%m-%d')}.",
                        suggested_action="Skip importing this row or click to import as a new expense.",
                        approval_required=True
                    )
        return None

class ZeroOrNegativeAmountRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        amount = row_data.get("parsed_amount")
        if amount is not None:
            if amount == 0:
                return AnomalyResult(
                    anomaly_type="ZERO_AMOUNT",
                    severity="INFO",
                    description="This expense has a value of $0.00.",
                    suggested_action="Skip row or verify if zero is correct.",
                    approval_required=True
                )
            elif amount < 0:
                return AnomalyResult(
                    anomaly_type="NEGATIVE_AMOUNT_REFUND",
                    severity="WARNING",
                    description="This expense has a negative amount, indicating a refund.",
                    suggested_action="Import as a refund (this will credit split members and debit the payer).",
                    approval_required=True
                )
        return None

class SplitDetailsMismatchRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        split_type = str(row_data.get("split_type") or "").strip().lower()
        split_details = str(row_data.get("split_details") or "").strip()
        
        if split_type == "percentage" and split_details:
            # Parse percentages, e.g. "Aisha 30%; Rohan 30%; Priya 30%; Meera 20%"
            matches = re.findall(r"(\d+(?:\.\d+)?)%", split_details)
            if matches:
                total_pct = sum(Decimal(m) for m in matches)
                if total_pct != Decimal("100"):
                    return AnomalyResult(
                        anomaly_type="PERCENTAGE_SUM_MISMATCH",
                        severity="CRITICAL",
                        description=f"Percentages in split details sum to {total_pct}% instead of 100%.",
                        suggested_action="Adjust percentages to total 100% or split equally.",
                        approval_required=True
                    )
        elif split_type == "unequal" or split_type == "exact":
            # Exact amounts
            amount_cents = row_data.get("parsed_amount")
            if amount_cents is not None:
                matches = re.findall(r"(\d+(?:\.\d+)?)", split_details)
                # Note: splits might be in dollars or cents. We will check if sum matches.
                # If numbers sum to amount (or amount/100), we validate it.
                if matches:
                    total_split = sum(Decimal(m) for m in matches)
                    # Try both absolute dollars and cents
                    if total_split != Decimal(amount_cents) and total_split * Decimal("100") != Decimal(amount_cents):
                        return AnomalyResult(
                            anomaly_type="EXACT_SPLIT_SUM_MISMATCH",
                            severity="CRITICAL",
                            description="Sum of individual splits does not match total expense amount.",
                            suggested_action="Recalculate splits to match the total amount exactly.",
                            approval_required=True
                        )
        return None

class SettlementRecordRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        description = str(row_data.get("description") or "").strip().lower()
        split_type = str(row_data.get("split_type") or "").strip().lower()
        notes = str(row_data.get("notes") or "").strip().lower()
        
        is_settlement = "paid back" in description or "settled" in description or "settlement" in notes or "settlement" in description
        if is_settlement or not split_type:
            return AnomalyResult(
                anomaly_type="SETTLEMENT_RECORD",
                severity="INFO",
                description="This row looks like a peer-to-peer settlement payment rather than a consumption expense.",
                suggested_action="Import as a Settlement transaction rather than an Expense.",
                approval_required=True
            )
        return None

class CurrencyConversionRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        currency = str(row_data.get("currency") or "INR").strip().upper()
        if currency != "INR" and currency != "":
            return AnomalyResult(
                anomaly_type="FOREIGN_CURRENCY",
                severity="WARNING",
                description=f"Transaction is in foreign currency '{currency}'.",
                suggested_action="Apply exchange rate (default: 1 USD = 83 INR) or enter amount in INR.",
                approval_required=True
            )
        return None

class DateAmbiguityRule(AnomalyRule):
    def detect(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[AnomalyResult]:
        date_str = str(row_data.get("date") or "").strip()
        if not date_str:
            return AnomalyResult(
                anomaly_type="MISSING_DATE",
                severity="CRITICAL",
                description="Date field is empty.",
                suggested_action="Provide a valid date.",
                approval_required=True
            )
            
        # Try parsing dates
        parsed_date = context.get("parsed_date")
        if not parsed_date:
            return AnomalyResult(
                anomaly_type="INVALID_DATE_FORMAT",
                severity="CRITICAL",
                description=f"Date '{date_str}' could not be parsed.",
                suggested_action="Input date in DD-MM-YYYY format.",
                approval_required=True
            )

        # Check for day-month ambiguity (e.g. 04-05-2026 can be April 5 or May 4)
        # We flag it if both day and month are <= 12 and the separator is - or /
        parts = re.split(r"[-/]", date_str)
        if len(parts) >= 2:
            try:
                p1, p2 = int(parts[0]), int(parts[1])
                if 1 <= p1 <= 12 and 1 <= p2 <= 12 and p1 != p2:
                    return AnomalyResult(
                        anomaly_type="DATE_AMBIGUITY_WARNING",
                        severity="INFO",
                        description=f"Date '{date_str}' is ambiguous (could be Day/Month or Month/Day).",
                        suggested_action="Confirm date format (interpreted as Day={0}, Month={1}).".format(parsed_date.day, parsed_date.month),
                        approval_required=False
                    )
            except ValueError:
                pass

        # Check if date is in the future
        if parsed_date > datetime.now(timezone.utc):
            return AnomalyResult(
                anomaly_type="FUTURE_DATE",
                severity="WARNING",
                description=f"Transaction date {parsed_date.strftime('%Y-%m-%d')} is in the future.",
                suggested_action="Adjust date to today.",
                approval_required=True
            )
            
        return None

# ----------------- Anomaly Framework Engine -----------------

class AnomalyEngine:
    def __init__(self):
        self.rules: List[AnomalyRule] = []
        self._register_default_rules()

    def register_rule(self, rule: AnomalyRule):
        self.rules.append(rule)

    def _register_default_rules(self):
        self.register_rule(MissingPayerRule())
        self.register_rule(InactiveMemberRule())
        self.register_rule(DuplicateExpenseRule())
        self.register_rule(ZeroOrNegativeAmountRule())
        self.register_rule(SplitDetailsMismatchRule())
        self.register_rule(SettlementRecordRule())
        self.register_rule(CurrencyConversionRule())
        self.register_rule(DateAmbiguityRule())

    def scan_record(self, row_data: Dict[str, Any], context: Dict[str, Any]) -> List[AnomalyResult]:
        anomalies = []
        # Pre-parse amount and date to make checks easier
        row_copy = row_data.copy()
        
        # Parse Amount
        raw_amount = str(row_copy.get("amount") or "").replace(",", "").strip()
        parsed_amount = None
        try:
            if raw_amount:
                # handles float or integer
                parsed_amount = int(round(float(raw_amount) * 100))
        except ValueError:
            pass
        row_copy["parsed_amount"] = parsed_amount
        context["parsed_amount"] = parsed_amount

        # Parse Date
        raw_date = str(row_copy.get("date") or "").strip()
        parsed_date = None
        # Try multiple formats
        for fmt in ("%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y-%m-%d", "%b-%d-%Y", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt)
                break
            except ValueError:
                continue
                
        # Handle special formats like "Mar-14" -> assuming current year 2026 (or file context year)
        if not parsed_date:
            match = re.match(r"^([a-zA-Z]{3})-(\d{1,2})$", raw_date)
            if match:
                try:
                    month_str, day_str = match.groups()
                    parsed_date = datetime.strptime(f"{day_str}-{month_str}-2026", "%d-%b-%Y")
                except ValueError:
                    pass

        if parsed_date:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
        context["parsed_date"] = parsed_date

        for rule in self.rules:
            res = rule.detect(row_copy, context)
            if res:
                anomalies.append(res)
                
        return anomalies

anomaly_engine = AnomalyEngine()
