import io
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from app.models.user import User
from app.models.group import Group, GroupMembership
from app.models.expense import Expense
from app.models.settlement import Settlement
from app.core.security import get_password_hash

def test_csv_upload_and_approval_integration(client, db):
    # 1. Seed users and a group
    pw = get_password_hash("password")
    alice = User(email="alice@test.com", name="Alice", password_hash=pw)
    bob = User(email="bob@test.com", name="Bob", password_hash=pw)
    db.add_all([alice, bob])
    db.flush()

    group = Group(name="Trippers", description="Road trip")
    db.add(group)
    db.flush()

    # Create memberships
    db.add(GroupMembership(group_id=group.id, user_id=alice.id, joined_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    db.add(GroupMembership(group_id=group.id, user_id=bob.id, joined_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    db.commit()

    # Login as Alice
    login_res = client.post("/api/auth/login", json={
        "email": "alice@test.com",
        "password": "password"
    })
    print("DEBUG LOGIN:", login_res.status_code, login_res.text)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload a mock CSV containing:
    # - A valid equal expense
    # - A typo in payer (Alice S -> should map to Alice)
    # - A settlement (Bob paid Alice back)
    csv_content = (
        "date,description,paid_by,amount,currency,split_type,split_with,split_details,notes\n"
        "10-02-2026,Dinner,Alice,3000,INR,equal,Alice;Bob,,\n"
        "12-02-2026,Snacks,Alice S,1000,INR,equal,Alice;Bob,,\n"
        "14-02-2026,Bob paid Alice back,Bob,500,INR,,Alice,,\n"
    )

    file_payload = {
        "file": ("test_expenses.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }

    upload_res = client.post(
        f"/api/groups/{group.id}/imports/upload",
        files=file_payload,
        headers=headers
    )
    print("DEBUG UPLOAD:", upload_res.status_code, upload_res.text)
    assert upload_res.status_code == 200
    import_data = upload_res.json()
    import_id = import_data["id"]
    assert import_data["status"] == "PENDING_REVIEW"
    assert len(import_data["records"]) == 3

    # Check that the unresolved payer anomaly was detected for row 2 (Alice S)
    record_with_anomaly = import_data["records"][1]
    anom_types = [a["anomaly_type"] for a in record_with_anomaly["anomalies"]]
    assert "UNRESOLVED_PAYER" in anom_types

    # 3. Submit resolutions
    # - Row 1 (rec[0]): Import directly
    # - Row 2 (rec[1]): Correct payer mapping to Alice
    # - Row 3 (rec[2]): Import directly (will be auto-detected as a Settlement)
    rec1_id = import_data["records"][0]["id"]
    rec2_id = import_data["records"][1]["id"]
    rec3_id = import_data["records"][2]["id"]

    resolutions = [
        {"record_id": rec1_id, "action": "IMPORT", "corrected_data": None},
        {
            "record_id": rec2_id,
            "action": "IMPORT",
            "corrected_data": {
                "paid_by_user_id": str(alice.id)
            }
        },
        {"record_id": rec3_id, "action": "IMPORT", "corrected_data": None}
    ]

    approve_res = client.post(
        f"/api/imports/{import_id}/approve",
        json={"resolutions": resolutions},
        headers=headers
    )
    
    assert approve_res.status_code == 200
    report = approve_res.json()
    assert report["imported_expenses"] == 2
    assert report["imported_settlements"] == 1

    # Verify database updates
    db.expire_all()
    expenses = db.query(Expense).filter(Expense.group_id == group.id).all()
    assert len(expenses) == 2
    assert expenses[0].amount == 300000
    assert expenses[1].amount == 100000
    assert expenses[1].paid_by_user_id == alice.id

    settlements = db.query(Settlement).filter(Settlement.group_id == group.id).all()
    assert len(settlements) == 1
    assert settlements[0].amount == 50000
    assert settlements[0].from_user_id == bob.id
    assert settlements[0].to_user_id == alice.id


def test_csv_approval_validation_errors(client, db):
    # Seed group and members
    pw = get_password_hash("password")
    alice = User(email="alice@test.com", name="Alice", password_hash=pw)
    db.add(alice)
    db.flush()

    group = Group(name="Trippers", description="Road trip")
    db.add(group)
    db.flush()

    db.add(GroupMembership(group_id=group.id, user_id=alice.id, joined_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    db.commit()

    # Login as Alice
    login_res = client.post("/api/auth/login", json={
        "email": "alice@test.com",
        "password": "password"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload CSV with empty payer and empty settlement receiver
    csv_content = (
        "date,description,paid_by,amount,currency,split_type,split_with,split_details,notes\n"
        "10-02-2026,Dinner,,3000,INR,equal,Alice,,\n"
        "14-02-2026,Alice paid back,Alice,500,INR,, ,,\n"
    )

    file_payload = {
        "file": ("test_validation.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    }

    upload_res = client.post(
        f"/api/groups/{group.id}/imports/upload",
        files=file_payload,
        headers=headers
    )
    assert upload_res.status_code == 200
    import_data = upload_res.json()
    import_id = import_data["id"]

    rec1_id = import_data["records"][0]["id"]
    rec2_id = import_data["records"][1]["id"]

    # Try to approve first row (missing payer) without resolution mapping -> should fail 400
    resolutions = [
        {"record_id": rec1_id, "action": "IMPORT", "corrected_data": None},
        {"record_id": rec2_id, "action": "SKIP", "corrected_data": None}
    ]
    approve_res = client.post(
        f"/api/imports/{import_id}/approve",
        json={"resolutions": resolutions},
        headers=headers
    )
    assert approve_res.status_code == 400
    assert "Payer is missing" in approve_res.json()["detail"]

    # Try to approve second row (missing receiver in settlement) without mapping -> should fail 400
    resolutions = [
        {"record_id": rec1_id, "action": "SKIP", "corrected_data": None},
        {"record_id": rec2_id, "action": "IMPORT", "corrected_data": None}
    ]
    approve_res = client.post(
        f"/api/imports/{import_id}/approve",
        json={"resolutions": resolutions},
        headers=headers
    )
    assert approve_res.status_code == 400
    assert "Settlement receiver is missing" in approve_res.json()["detail"]

