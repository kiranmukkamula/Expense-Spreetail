import csv
import io
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.group import GroupMembership
from app.models.expense import Expense
from app.models.imports import CSVImport, ImportRecord, ImportAnomaly
from app.services.anomalies import anomaly_engine

def parse_and_stage_csv(
    group_id: Any,
    uploader_id: Any,
    filename: str,
    file_content: bytes,
    db: Session
) -> CSVImport:
    # 1. Create CSVImport entry in DB
    csv_import = CSVImport(
        group_id=group_id,
        uploaded_by_user_id=uploader_id,
        filename=filename,
        status="PENDING_REVIEW"
    )
    db.add(csv_import)
    db.flush()

    # 2. Gather context for anomaly detection
    # A. Group members details
    memberships = db.query(GroupMembership).filter(GroupMembership.group_id == group_id).all()
    group_members = []
    for m in memberships:
        group_members.append({
            "id": m.user_id,
            "name": m.user.name,
            "email": m.user.email,
            "joined_at": m.joined_at,
            "left_at": m.left_at
        })

    # B. Existing expenses in DB
    existing_expenses = db.query(Expense).filter(Expense.group_id == group_id).all()

    # 3. Read CSV content
    text_stream = io.StringIO(file_content.decode("utf-8-sig"))
    csv_reader = csv.DictReader(text_stream)

    # Clean headers (strip spaces)
    if csv_reader.fieldnames:
        csv_reader.fieldnames = [f.strip().lower() for f in csv_reader.fieldnames]

    rows = list(csv_reader)
    uploaded_rows = []
    
    # We pre-clean row keys and values to avoid lookup errors
    for r in rows:
        cleaned_row = {}
        for k, v in r.items():
            if k:
                cleaned_row[k.strip().lower()] = v
        uploaded_rows.append(cleaned_row)

    # 4. Process each row
    for index, row_data in enumerate(uploaded_rows):
        # Build evaluation context
        context = {
            "group_members": group_members,
            "existing_expenses": existing_expenses,
            "uploaded_rows": uploaded_rows,
            "row_index": index,
            "db": db
        }

        # Scan row for anomalies
        anomalies = anomaly_engine.scan_record(row_data, context)

        # Create ImportRecord
        import_record = ImportRecord(
            import_id=csv_import.id,
            row_index=index,
            raw_data=row_data,
            status="PENDING"
        )
        db.add(import_record)
        db.flush()

        # Save any anomalies found
        for anomaly in anomalies:
            db_anomaly = ImportAnomaly(
                import_record_id=import_record.id,
                anomaly_type=anomaly.anomaly_type,
                severity=anomaly.severity,
                description=anomaly.description,
                suggested_action=anomaly.suggested_action,
                is_approved=None
            )
            db.add(db_anomaly)

    db.commit()
    db.refresh(csv_import)
    return csv_import
