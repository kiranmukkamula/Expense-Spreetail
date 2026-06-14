from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional, Any, Dict

class AnomalyOut(BaseModel):
    id: UUID
    anomaly_type: str
    severity: str
    description: str
    suggested_action: str
    is_approved: Optional[bool] = None

    class Config:
        from_attributes = True

class ImportRecordOut(BaseModel):
    id: UUID
    row_index: int
    raw_data: Dict[str, Any]
    corrected_data: Optional[Dict[str, Any]] = None
    status: str
    anomalies: List[AnomalyOut] = []

    class Config:
        from_attributes = True

class CSVImportOut(BaseModel):
    id: UUID
    group_id: UUID
    filename: str
    status: str
    created_at: datetime
    records: List[ImportRecordOut] = []

    class Config:
        from_attributes = True

class ImportResolution(BaseModel):
    record_id: UUID
    action: str  # "IMPORT", "CORRECT", "SKIP"
    corrected_data: Optional[Dict[str, Any]] = None

class ImportResolveRequest(BaseModel):
    resolutions: List[ImportResolution]
