from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime, timezone
import re
from decimal import Decimal
from app.core.database import get_db
from app.models.group import GroupMembership, Group
from app.models.user import User
from app.models.expense import Expense, ExpenseSplit
from app.models.settlement import Settlement
from app.models.imports import CSVImport, ImportRecord, ImportAnomaly
from app.schemas.imports import CSVImportOut, ImportResolveRequest
from app.routers.deps import get_current_user
from app.services.csv_parser import parse_and_stage_csv
from app.services.balance_engine import calculate_splits
from typing import List, Dict, Any

router = APIRouter(tags=["imports"])

@router.post("/groups/{group_id}/imports/upload", response_model=CSVImportOut)
async def upload_csv(
    group_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify group membership
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized.")

    content = await file.read()
    try:
        csv_import = parse_and_stage_csv(
            group_id=group_id,
            uploader_id=current_user.id,
            filename=file.filename,
            file_content=content,
            db=db
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")

    # Fetch with relationships
    db.refresh(csv_import)
    return csv_import

@router.get("/groups/{group_id}/imports", response_model=List[CSVImportOut])
def list_imports(
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

    imports = db.query(CSVImport).filter(CSVImport.group_id == group_id).order_by(CSVImport.created_at.desc()).all()
    return imports

@router.get("/imports/{import_id}", response_model=CSVImportOut)
def get_import_details(
    import_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    csv_import = db.query(CSVImport).filter(CSVImport.id == import_id).first()
    if not csv_import:
        raise HTTPException(status_code=404, detail="Import not found.")

    # Check access to group
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == csv_import.group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized.")

    return csv_import

@router.post("/imports/{import_id}/approve")
def approve_import(
    import_id: UUID,
    resolve_in: ImportResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    csv_import = db.query(CSVImport).filter(CSVImport.id == import_id).first()
    if not csv_import:
        raise HTTPException(status_code=404, detail="Import not found.")
    
    if csv_import.status == "PROCESSED":
        raise HTTPException(status_code=400, detail="Import has already been processed.")

    # Check access
    group_id = csv_import.group_id
    membership = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized.")

    # Create mapping of record resolution
    resolutions_map = {res.record_id: res for res in resolve_in.resolutions}

    # Fetch all records
    records = db.query(ImportRecord).filter(ImportRecord.import_id == import_id).all()

    # Pre-fetch existing users in group to resolve names
    memberships = db.query(GroupMembership).filter(GroupMembership.group_id == group_id).all()
    group_members = {m.user.name.lower(): m.user for m in memberships}
    group_members_email = {m.user.email.lower(): m.user for m in memberships}

    # Internal helper to find/create user by name
    def get_or_create_user(name_str: str) -> User:
        name_clean = name_str.strip().lower()
        if not name_clean:
            # Fallback to avoid creating empty user name
            existing_unknown = db.query(User).filter(User.email == "unknown@split.local").first()
            if existing_unknown:
                return existing_unknown
            new_u = User(email="unknown@split.local", name="Unknown Payer", password_hash="")
            db.add(new_u)
            db.flush()
            return new_u

        if name_clean in group_members:
            return group_members[name_clean]
        
        # Check by email format
        if "@" in name_clean:
            if name_clean in group_members_email:
                return group_members_email[name_clean]
            
            # Find in all database users first
            existing = db.query(User).filter(User.email == name_clean).first()
            if existing:
                return existing
            
            # Create new user
            username = name_clean.split("@")[0].capitalize()
            new_u = User(email=name_clean, name=username, password_hash="")
            db.add(new_u)
            db.flush()
            return new_u
        else:
            # Match existing users in database by name
            existing = db.query(User).filter(func.lower(User.name) == name_clean).first()
            if existing:
                return existing
            
            # Create a mock email
            email_mock = f"{name_clean}@split.local"
            existing_email = db.query(User).filter(User.email == email_mock).first()
            if existing_email:
                return existing_email
            
            new_u = User(email=email_mock, name=name_str.strip().capitalize(), password_hash="")
            db.add(new_u)
            db.flush()
            return new_u

    imported_expenses_count = 0
    imported_settlements_count = 0

    try:
        # Loop through each record and apply resolutions
        for rec in records:
            res = resolutions_map.get(rec.id)
            action = res.action if res else "IMPORT"

            if action == "SKIP":
                rec.status = "SKIPPED"
                continue

            # Merge raw data with corrected data if resolution supplied overrides
            data = rec.raw_data.copy()
            if res and res.corrected_data:
                data.update(res.corrected_data)

            # 1. Parse amount (float or integer cents)
            raw_amount = str(data.get("amount") or "0").replace(",", "").strip()
            amount_cents = int(round(float(raw_amount) * 100))

            # 2. Currency conversion
            currency = str(data.get("currency") or "INR").strip().upper()
            if currency == "USD":
                # Apply conversion rate: 1 USD = 83 INR
                amount_cents = int(amount_cents * 83)
                currency = "INR"

            # 3. Parse date
            raw_date = str(data.get("date") or "").strip()
            expense_date = None
            for fmt in ("%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%Y-%m-%d", "%b-%d-%Y", "%Y/%m/%d"):
                try:
                    expense_date = datetime.strptime(raw_date, fmt)
                    break
                except ValueError:
                    continue
            if not expense_date:
                # Handle Mar-14 format
                match = re.match(r"^([a-zA-Z]{3})-(\d{1,2})$", raw_date)
                if match:
                    month_str, day_str = match.groups()
                    expense_date = datetime.strptime(f"{day_str}-{month_str}-2026", "%d-%b-%Y")
                else:
                    expense_date = datetime.now(timezone.utc)

            if expense_date and expense_date.tzinfo is None:
                expense_date = expense_date.replace(tzinfo=timezone.utc)

            # 4. Resolve Payer
            paid_by_str = str(data.get("paid_by") or "").strip()
            
            # Allow mapping override in corrected_data
            payer_uuid_str = data.get("paid_by_user_id")
            if payer_uuid_str:
                payer_user = db.query(User).filter(User.id == UUID(str(payer_uuid_str))).first()
                if not payer_user:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Row {rec.row_index + 1}: Selected payer mapping not found in database."
                    )
            else:
                if not paid_by_str:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Row {rec.row_index + 1}: Payer is missing. You must map the payer to a valid group member."
                    )
                payer_user = get_or_create_user(paid_by_str)

            # Ensure payer has membership on expense date (retroactive join if needed)
            payer_mem = db.query(GroupMembership).filter(
                GroupMembership.group_id == group_id,
                GroupMembership.user_id == payer_user.id
            ).first()
            if not payer_mem:
                payer_mem = GroupMembership(
                    group_id=group_id,
                    user_id=payer_user.id,
                    joined_at=expense_date - timedelta(days=1)
                )
                db.add(payer_mem)
                db.flush()
            else:
                payer_joined_naive = payer_mem.joined_at.replace(tzinfo=None) if payer_mem.joined_at.tzinfo else payer_mem.joined_at
                expense_date_naive = expense_date.replace(tzinfo=None) if expense_date.tzinfo else expense_date
                if payer_joined_naive > expense_date_naive:
                    # Extend joining date back to accommodate expense
                    payer_mem.joined_at = expense_date - timedelta(days=1)

            # 5. Check if Settlement
            description = str(data.get("description") or "").strip()
            split_type = str(data.get("split_type") or "").strip().lower()
            notes = str(data.get("notes") or "").strip().lower()

            is_settlement = (
                "paid back" in description.lower() 
                or "settled" in description.lower() 
                or "settlement" in notes 
                or "settlement" in description.lower()
                or not split_type
            )

            if is_settlement:
                # Record as settlement instead of expense
                # Split with / details will indicate who received it
                split_with_str = str(data.get("split_with") or "").split(";")[0].strip()
                if not split_with_str:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Row {rec.row_index + 1}: Settlement receiver is missing. You must map the receiver to a valid group member."
                    )
                receiver_user = get_or_create_user(split_with_str)

                # Ensure receiver is member
                receiver_mem = db.query(GroupMembership).filter(
                    GroupMembership.group_id == group_id,
                    GroupMembership.user_id == receiver_user.id
                ).first()
                if not receiver_mem:
                    receiver_mem = GroupMembership(
                        group_id=group_id,
                        user_id=receiver_user.id,
                        joined_at=expense_date - timedelta(days=1)
                    )
                    db.add(receiver_mem)
                    db.flush()

                settlement = Settlement(
                    group_id=group_id,
                    from_user_id=payer_user.id,
                    to_user_id=receiver_user.id,
                    amount=amount_cents,
                    currency=currency,
                    settlement_date=expense_date
                )
                db.add(settlement)
                imported_settlements_count += 1
                rec.status = "PROCESSED"
                continue

            # 6. Parse splits participants
            split_with_raw = str(data.get("split_with") or "").strip()
            if not split_with_raw:
                # Fallback: all active group members at date
                active_mem = db.query(GroupMembership).filter(
                    GroupMembership.group_id == group_id,
                    GroupMembership.joined_at <= expense_date,
                    (GroupMembership.left_at == None) | (GroupMembership.left_at > expense_date)
                ).all()
                participants = [m.user for m in active_mem]
            else:
                participants = [get_or_create_user(name) for name in split_with_raw.split(";") if name.strip()]

            # Ensure all participants have group memberships
            for p in participants:
                p_mem = db.query(GroupMembership).filter(
                    GroupMembership.group_id == group_id,
                    GroupMembership.user_id == p.id
                ).first()
                if not p_mem:
                    p_mem = GroupMembership(
                        group_id=group_id,
                        user_id=p.id,
                        joined_at=expense_date - timedelta(days=1)
                    )
                    db.add(p_mem)
                    db.flush()
                elif p_mem.left_at:
                    p_left_naive = p_mem.left_at.replace(tzinfo=None) if p_mem.left_at.tzinfo else p_mem.left_at
                    expense_date_naive = expense_date.replace(tzinfo=None) if expense_date.tzinfo else expense_date
                    if p_left_naive <= expense_date_naive:
                        # Inactive member during split: clear their left_at or extend it
                        p_mem.left_at = None

            # 7. Parse splits share values
            split_details_str = str(data.get("split_details") or "").strip()
            share_values = []
            
            # Prepare values based on split type
            s_type = split_type.upper()
            if s_type == "EQUAL":
                share_values = [Decimal("1.0")] * len(participants)
            elif s_type == "PERCENTAGE":
                # Parse Aisha 30%; Rohan 30%
                pct_map = {}
                for item in split_details_str.split(";"):
                    if not item.strip():
                        continue
                    m = re.match(r"([a-zA-Z0-9\s]+?)\s+(\d+(?:\.\d+)?)\s*%", item)
                    if m:
                        name, pct = m.groups()
                        pct_map[name.strip().lower()] = Decimal(pct)
                
                # Align with participants
                for p in participants:
                    val = pct_map.get(p.name.lower()) or pct_map.get(p.email.lower()) or Decimal("0")
                    share_values.append(val)
            elif s_type == "SHARE":
                # Parse Aisha 1; Rohan 2
                share_map = {}
                for item in split_details_str.split(";"):
                    if not item.strip():
                        continue
                    m = re.match(r"([a-zA-Z0-9\s]+?)\s+(\d+(?:\.\d+)?)", item)
                    if m:
                        name, sh = m.groups()
                        share_map[name.strip().lower()] = Decimal(sh)
                
                for p in participants:
                    val = share_map.get(p.name.lower()) or share_map.get(p.email.lower()) or Decimal("1")
                    share_values.append(val)
            elif s_type == "UNEQUAL" or s_type == "EXACT":
                s_type = "EXACT"
                exact_map = {}
                for item in split_details_str.split(";"):
                    if not item.strip():
                        continue
                    m = re.match(r"([a-zA-Z0-9\s]+?)\s+(\d+(?:\.\d+)?)", item)
                    if m:
                        name, amt = m.groups()
                        # Convert to cents
                        exact_map[name.strip().lower()] = Decimal(int(round(float(amt) * 100)))
                
                for p in participants:
                    val = exact_map.get(p.name.lower()) or exact_map.get(p.email.lower()) or Decimal("0")
                    share_values.append(val)

            # Compute actual split amounts
            cents_amounts = calculate_splits(
                amount_cents,
                s_type,
                [p.id for p in participants],
                share_values
            )

            # Save Expense
            expense = Expense(
                group_id=group_id,
                paid_by_user_id=payer_user.id,
                amount=amount_cents,
                description=description,
                split_type=s_type,
                currency=currency,
                expense_date=expense_date
            )
            db.add(expense)
            db.flush()

            # Save Splits
            for idx, p in enumerate(participants):
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=p.id,
                    share_value=share_values[idx],
                    calculated_amount=cents_amounts[idx]
                )
                db.add(split)

            imported_expenses_count += 1
            rec.status = "PROCESSED"

        # Update CSVImport status
        csv_import.status = "PROCESSED"
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to execute import approval. Database rolled back. Error: {str(e)}"
        )

    return {
        "status": "success",
        "imported_expenses": imported_expenses_count,
        "imported_settlements": imported_settlements_count
    }

# Time delta helper
from datetime import timedelta
