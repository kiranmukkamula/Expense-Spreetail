from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class MemberUserOut(BaseModel):
    id: UUID
    email: str
    name: str

class MemberOut(BaseModel):
    id: UUID
    user: MemberUserOut
    joined_at: datetime
    left_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class GroupOut(GroupBase):
    id: UUID
    created_at: datetime
    memberships: List[MemberOut] = []

    class Config:
        from_attributes = True

class MemberAdd(BaseModel):
    email: str  # We can invite by email address
