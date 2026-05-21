"""Optional scan history persistence (SQLite via SQLModel)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from globeye.core.models import ScanResult
from globeye.report.json_writer import to_dict


class ScanRecord(SQLModel, table=True):
    """One persisted scan."""

    id: int | None = Field(default=None, primary_key=True)
    target_value: str = Field(index=True)
    target_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_findings: int = 0
    summary_json: str = "{}"
    result_json: str = "{}"
    model_json: str = "{}"


def make_engine(db_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        path = db_url.split("sqlite:///")[-1]
        if path and path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(db_url, connect_args=connect_args)
    SQLModel.metadata.create_all(engine)
    return engine


def save_scan(engine: Engine, result: ScanResult) -> int:
    payload = to_dict(result)
    record = ScanRecord(
        target_value=result.target.value,
        target_type=result.target.type.value,
        total_findings=len(result.findings),
        summary_json=json.dumps(payload["summary"]),
        result_json=json.dumps(payload),
        model_json=result.model_dump_json(),
    )
    with Session(engine) as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return int(record.id or 0)


def list_scans(engine: Engine, limit: int = 50) -> list[ScanRecord]:
    with Session(engine) as session:
        stmt = select(ScanRecord).order_by(col(ScanRecord.id).desc()).limit(limit)
        return list(session.exec(stmt).all())


def get_scan(engine: Engine, scan_id: int) -> ScanRecord | None:
    with Session(engine) as session:
        return session.get(ScanRecord, scan_id)
