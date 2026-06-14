from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from app.core.database import get_db
from app.models.expense import Expense, ExpenseSplit
from app.models.group import GroupMembership
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseOut
from app.routers.deps import get_current_user
from app.services.balance_engine import calculate_splits
from typing import List
from decimal import Decimal

router = APIRouter(prefix="/groups/{group_id}/expenses", tags=["expenses"])

@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: UUID,
    expense_in: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify caller access to group
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this group.")

    # Determine splits
    participants = []
    share_values = []
    
    # 1. If split is EQUAL and splits list is empty, auto-populate with active group members on that date
    if expense_in.split_type.upper() == "EQUAL" and not expense_in.splits:
        active_memberships = db.query(GroupMembership).filter(
            GroupMembership.group_id == group_id,
            GroupMembership.joined_at <= expense_in.expense_date,
            (GroupMembership.left_at == None) | (GroupMembership.left_at > expense_in.expense_date)
        ).all()
        
        if not active_memberships:
            raise HTTPException(
                status_code=400,
                detail="No active group members found on the specified expense date."
            )
            
        for m in active_memberships:
            participants.append(m.user_id)
            share_values.append(Decimal("1.0"))
    else:
        for s in expense_in.splits:
            # Verify split user is in group
            user_exists = db.query(GroupMembership).filter(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id == s.user_id
            ).first()
            if not user_exists:
                raise HTTPException(status_code=400, detail=f"User {s.user_id} is not a member of the group.")
            participants.append(s.user_id)
            share_values.append(s.share_value)

    # 2. Math split calculation
    from decimal import Decimal
    decimal_shares = [Decimal(str(v)) for v in share_values]
    cents_amounts = calculate_splits(expense_in.amount, expense_in.split_type, participants, decimal_shares)

    # Verify matching split sum
    if sum(cents_amounts) != expense_in.amount:
        raise HTTPException(
            status_code=400,
            detail="The sum of the calculated splits does not match the total amount."
        )

    # 3. Save to database in a single transaction
    expense = Expense(
        group_id=group_id,
        paid_by_user_id=expense_in.paid_by_user_id,
        amount=expense_in.amount,
        description=expense_in.description,
        split_type=expense_in.split_type.upper(),
        currency=expense_in.currency,
        expense_date=expense_in.expense_date
    )
    db.add(expense)
    db.flush()

    for idx, user_id in enumerate(participants):
        split = ExpenseSplit(
            expense_id=expense.id,
            user_id=user_id,
            share_value=share_values[idx],
            calculated_amount=cents_amounts[idx]
        )
        db.add(split)

    db.commit()
    db.refresh(expense)
    return expense

@router.get("", response_model=List[ExpenseOut])
def list_expenses(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check group membership
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized.")

    expenses = db.query(Expense).filter(Expense.group_id == group_id).order_by(Expense.expense_date.desc()).all()
    return expenses
