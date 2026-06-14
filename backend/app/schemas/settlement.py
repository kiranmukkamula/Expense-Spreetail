from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class SettlementCreate(BaseModel):
    from_user_id: UUID
    to_user_id: UUID
    amount: int  # in cents
    currency: str = "INR"
    settlement_date: datetime

class SettlementOut(BaseModel):
    id: UUID
    group_id: UUID
    from_user_id: UUID
    to_user_id: UUID
    amount: int
    currency: str
    settlement_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True
