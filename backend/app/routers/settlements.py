from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.models.settlement import Settlement
from app.models.group import GroupMembership
from app.models.user import User
from app.schemas.settlement import SettlementCreate, SettlementOut
from app.routers.deps import get_current_user
from typing import List

router = APIRouter(prefix="/groups/{group_id}/settlements", tags=["settlements"])

@router.post("", response_model=SettlementOut, status_code=status.HTTP_201_CREATED)
def create_settlement(
    group_id: UUID,
    settlement_in: SettlementCreate,
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

    # Verify that both from and to users are members of the group
    from_mem = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == settlement_in.from_user_id
    ).first()
    to_mem = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == settlement_in.to_user_id
    ).first()

    if not from_mem or not to_mem:
        raise HTTPException(
            status_code=400,
            detail="Both sender and receiver must be members of the group."
        )

    # Save settlement record
    settlement = Settlement(
        group_id=group_id,
        from_user_id=settlement_in.from_user_id,
        to_user_id=settlement_in.to_user_id,
        amount=settlement_in.amount,
        currency=settlement_in.currency,
        settlement_date=settlement_in.settlement_date
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement

@router.get("", response_model=List[SettlementOut])
def list_settlements(
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

    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).order_by(Settlement.settlement_date.desc()).all()
    return settlements
