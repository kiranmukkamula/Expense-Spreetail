from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

class SplitDetail(BaseModel):
    user_id: UUID
    share_value: Decimal = Field(..., max_digits=10, decimal_places=4)

class ExpenseCreate(BaseModel):
    description: str
    amount: int  # in cents
    paid_by_user_id: UUID
    split_type: str  # EQUAL, EXACT, PERCENTAGE, SHARE
    currency: str = "INR"
    expense_date: datetime
    splits: List[SplitDetail]

class SplitOut(BaseModel):
    id: UUID
    user_id: UUID
    share_value: Decimal
    calculated_amount: int

    class Config:
        from_attributes = True

class ExpenseOut(BaseModel):
    id: UUID
    group_id: UUID
    paid_by_user_id: UUID
    amount: int
    description: str
    split_type: str
    currency: str
    expense_date: datetime
    created_at: datetime
    splits: List[SplitOut] = []

    class Config:
        from_attributes = True
