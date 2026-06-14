from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import UUID
from app.core.database import get_db
from app.models.group import Group, GroupMembership
from app.models.user import User
from app.schemas.group import GroupCreate, GroupOut, MemberAdd
from app.routers.deps import get_current_user
from typing import List

router = APIRouter(prefix="/groups", tags=["groups"])

@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(group_in: GroupCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Create group
    group = Group(name=group_in.name, description=group_in.description)
    db.add(group)
    db.flush()

    # Automatically add creator as first active member
    membership = GroupMembership(
        group_id=group.id,
        user_id=current_user.id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(membership)
    db.commit()
    db.refresh(group)
    return group

@router.get("", response_model=List[GroupOut])
def list_groups(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # List groups where user is a member (either active or historical)
    groups = db.query(Group).join(GroupMembership).filter(
        GroupMembership.user_id == current_user.id
    ).all()
    return groups

@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check access
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this group.")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found.")
    return group

@router.post("/{group_id}/members", status_code=status.HTTP_200_OK)
def add_group_member(
    group_id: UUID,
    member_in: MemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify group access
    creator_member = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not creator_member:
        raise HTTPException(status_code=403, detail="Not authorized to add members to this group.")

    # Find or create user
    email_clean = member_in.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        # Create a placeholder user
        name_part = email_clean.split("@")[0].capitalize()
        user = User(email=email_clean, name=name_part, password_hash="")
        db.add(user)
        db.flush()

    # Check if already a member
    existing = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == user.id,
        GroupMembership.left_at == None
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User is already an active member of this group.")

    # Create new membership
    new_mem = GroupMembership(
        group_id=group_id,
        user_id=user.id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(new_mem)
    db.commit()
    return {"status": "success", "message": f"Added {user.name} to the group."}

@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_group_member(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify group access
    creator_member = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not creator_member:
        raise HTTPException(status_code=403, detail="Not authorized.")

    # Find active membership
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == user_id,
        GroupMembership.left_at == None
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="Active membership not found.")

    # Mark left
    membership.left_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "User marked as inactive in group.", "left_at": membership.left_at}
