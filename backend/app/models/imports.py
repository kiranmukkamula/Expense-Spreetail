import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.guid_helper import GUID

class CSVImport(Base):
    __tablename__ = "csv_imports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_user_id = Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default="PENDING_REVIEW", nullable=False)  # PENDING_REVIEW, PROCESSED, REJECTED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group")
    uploader = relationship("User")
    records = relationship("ImportRecord", back_populates="csv_import", cascade="all, delete-orphan")

class ImportRecord(Base):
    __tablename__ = "import_records"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    import_id = Column(GUID(), ForeignKey("csv_imports.id", ondelete="CASCADE"), nullable=False)
    row_index = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)  # CSV headers -> values
    corrected_data = Column(JSON, nullable=True)  # Modified row data
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, VALIDATED, SKIPPED, PROCESSED

    csv_import = relationship("CSVImport", back_populates="records")
    anomalies = relationship("ImportAnomaly", back_populates="record", cascade="all, delete-orphan")

class ImportAnomaly(Base):
    __tablename__ = "import_anomalies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    import_record_id = Column(GUID(), ForeignKey("import_records.id", ondelete="CASCADE"), nullable=False)
    anomaly_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)  # INFO, WARNING, CRITICAL
    description = Column(String(1024), nullable=False)
    suggested_action = Column(String(1024), nullable=False)
    is_approved = Column(Boolean, nullable=True, default=None)  # None = pending user action, True = approved, False = rejected

    record = relationship("ImportRecord", back_populates="anomalies")
