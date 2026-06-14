import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.guid_helper import GUID

class Settlement(Base):
    __tablename__ = "settlements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    from_user_id = Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    to_user_id = Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount = Column(Integer, nullable=False)  # in cents
    currency = Column(String(10), default="INR", nullable=False)
    settlement_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="settlements")
    debtor = relationship("User", foreign_keys=[from_user_id])
    creditor = relationship("User", foreign_keys=[to_user_id])
