import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.guid_helper import GUID

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    paid_by_user_id = Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Integer, nullable=False)  # in cents
    description = Column(String(255), nullable=False)
    split_type = Column(String(50), nullable=False)  # EQUAL, EXACT, PERCENTAGE, SHARE
    currency = Column(String(10), default="INR", nullable=False)
    expense_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="expenses")
    payer = relationship("User")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")

class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    expense_id = Column(GUID(), ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    share_value = Column(Numeric(10, 4), nullable=False)  # holds percentage, share count, etc.
    calculated_amount = Column(Integer, nullable=False)  # final split in cents

    expense = relationship("Expense", back_populates="splits")
    user = relationship("User")
