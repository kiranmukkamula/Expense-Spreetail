from uuid import UUID
from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.expense import Expense, ExpenseSplit
from app.models.settlement import Settlement
from app.models.group import GroupMembership

def calculate_splits(amount_cents: int, split_type: str, participants: List[UUID], share_values: List[Decimal]) -> List[int]:
    """
    Computes split amounts in integer cents for each participant.
    Ensures that sum(splits) == amount_cents exactly by distributing rounding remainders.
    """
    n = len(participants)
    if n == 0:
        return []

    split_type = split_type.upper()
    calculated_amounts = [0] * n

    if split_type == "EQUAL":
        base = amount_cents // n
        remainder = amount_cents % n
        for i in range(n):
            calculated_amounts[i] = base + (1 if i < remainder else 0)

    elif split_type == "EXACT":
        # share_values contain exact cent amounts.
        # We just convert to int and verify.
        total_shares = 0
        for i in range(n):
            val = int(round(share_values[i]))
            calculated_amounts[i] = val
            total_shares += val
        
        # In case there's an exact mismatch, we don't auto-correct here; we assume validation caught it.
        # However, to be safe, we check if total matches. If not, we distribute difference to first user.
        diff = amount_cents - total_shares
        if diff != 0:
            calculated_amounts[0] += diff

    elif split_type == "PERCENTAGE":
        # share_values are percentages (e.g. 33.3333)
        # calculated_amount = amount_cents * (percentage / 100)
        total_pct = sum(share_values)
        temp_sum = 0
        for i in range(n):
            # Use Decimal for high precision
            share_pct = share_values[i]
            val = int(amount_cents * share_pct / Decimal("100.00"))
            calculated_amounts[i] = val
            temp_sum += val
        
        diff = amount_cents - temp_sum
        # Distribute remaining cents
        for i in range(abs(diff)):
            idx = i % n
            calculated_amounts[idx] += (1 if diff > 0 else -1)

    elif split_type == "SHARE":
        # share_values are shares (e.g. 2, 1, 1)
        total_shares = sum(share_values)
        if total_shares == 0:
            # Fallback to equal splits if shares are zero
            return calculate_splits(amount_cents, "EQUAL", participants, share_values)
        
        temp_sum = 0
        for i in range(n):
            val = int(amount_cents * share_values[i] / total_shares)
            calculated_amounts[i] = val
            temp_sum += val
        
        diff = amount_cents - temp_sum
        for i in range(abs(diff)):
            idx = i % n
            calculated_amounts[idx] += (1 if diff > 0 else -1)

    return calculated_amounts

def calculate_group_balances(group_id: UUID, db: Session) -> Dict[UUID, int]:
    """
    Calculates the current net balance for each group member.
    Formula: Net = Paid - Owed + SentSettlements - ReceivedSettlements
    """
    # 1. Fetch all members who are or were in the group
    memberships = db.query(GroupMembership).filter(GroupMembership.group_id == group_id).all()
    user_ids = {m.user_id for m in memberships}
    balances = {uid: 0 for uid in user_ids}

    # 2. Add credits for expenses paid
    payments = db.query(
        Expense.paid_by_user_id, func.sum(Expense.amount)
    ).filter(Expense.group_id == group_id).group_by(Expense.paid_by_user_id).all()

    for payer_id, total_paid in payments:
        if payer_id in balances:
            balances[payer_id] += int(total_paid)

    # 3. Subtract obligations (splits)
    obligations = db.query(
        ExpenseSplit.user_id, func.sum(ExpenseSplit.calculated_amount)
    ).join(Expense).filter(Expense.group_id == group_id).group_by(ExpenseSplit.user_id).all()

    for user_id, total_owed in obligations:
        if user_id in balances:
            balances[user_id] -= int(total_owed)

    # 4. Add settlements sent
    sent_settlements = db.query(
        Settlement.from_user_id, func.sum(Settlement.amount)
    ).filter(Settlement.group_id == group_id).group_by(Settlement.from_user_id).all()

    for sender_id, total_sent in sent_settlements:
        if sender_id in balances:
            balances[sender_id] += int(total_sent)

    # 5. Subtract settlements received
    received_settlements = db.query(
        Settlement.to_user_id, func.sum(Settlement.amount)
    ).filter(Settlement.group_id == group_id).group_by(Settlement.to_user_id).all()

    for receiver_id, total_received in received_settlements:
        if receiver_id in balances:
            balances[receiver_id] -= int(total_received)

    return balances

def simplify_debts(balances: Dict[UUID, int]) -> List[Dict]:
    """
    Applies the min-flow algorithm to simplify transactions.
    Returns list of dicts: {"from_user_id": UUID, "to_user_id": UUID, "amount": int}
    """
    debtors = []  # (balance, user_id) - negative balance
    creditors = []  # (balance, user_id) - positive balance

    for uid, bal in balances.items():
        if bal < 0:
            debtors.append([bal, uid])
        elif bal > 0:
            creditors.append([bal, uid])

    # Sort: debtors ascending (largest debt first), creditors descending (largest credit first)
    debtors.sort(key=lambda x: x[0])
    creditors.sort(key=lambda x: x[0], reverse=True)

    transactions = []
    d_idx = 0
    c_idx = 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor_bal, debtor_id = debtors[d_idx]
        creditor_bal, creditor_id = creditors[c_idx]

        amount = min(-debtor_bal, creditor_bal)
        if amount > 0:
            transactions.append({
                "from_user_id": debtor_id,
                "to_user_id": creditor_id,
                "amount": amount
            })

            # Update balances
            debtors[d_idx][0] += amount
            creditors[c_idx][0] -= amount

        # If debtor balance is now 0, move to next debtor
        if abs(debtors[d_idx][0]) < 1:
            d_idx += 1
        # If creditor balance is now 0, move to next creditor
        if creditors[c_idx][0] < 1:
            c_idx += 1

    return transactions
