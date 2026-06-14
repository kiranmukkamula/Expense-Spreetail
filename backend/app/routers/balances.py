from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from app.core.database import get_db
from app.models.group import GroupMembership
from app.models.user import User
from app.routers.deps import get_current_user
from app.services.balance_engine import calculate_group_balances, simplify_debts
from typing import Dict, List, Any

router = APIRouter(prefix="/groups/{group_id}/balances", tags=["balances"])

@router.get("", response_model=Dict[str, Any])
def get_balances(
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

    # Calculate net balances
    net_balances = calculate_group_balances(group_id, db)
    
    # Simplify debts
    simplified = simplify_debts(net_balances)

    # Fetch user details for representation
    users_info = {}
    db_users = db.query(User).filter(User.id.in_(list(net_balances.keys()))).all()
    for u in db_users:
        users_info[str(u.id)] = {
            "name": u.name,
            "email": u.email
        }

    # Format output
    formatted_balances = {}
    for uid, bal in net_balances.items():
        formatted_balances[str(uid)] = bal

    # Format simplified transactions with user details
    formatted_simplified = []
    for tx in simplified:
        from_id_str = str(tx["from_user_id"])
        to_id_str = str(tx["to_user_id"])
        formatted_simplified.append({
            "from_user_id": from_id_str,
            "from_user_name": users_info.get(from_id_str, {}).get("name", "Unknown"),
            "to_user_id": to_id_str,
            "to_user_name": users_info.get(to_id_str, {}).get("name", "Unknown"),
            "amount": tx["amount"]
        })

    return {
        "net_balances": formatted_balances,
        "users_info": users_info,
        "simplified_settlements": formatted_simplified
    }
