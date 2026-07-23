"""
Deterministic evaluation of privacy-conscious runtime audit metadata.
"""

import json
from collections.abc import Iterable, Mapping
from math import isfinite
from pathlib import Path
from typing import Any

from app.audit_log import AUDIT_LOG_PATH


RUNTIME_STATUSES = {"success", "failure", "timeout", "blocked"}
AUDIT_METADATA_FIELDS = (
    "timestamp",
    "agent_name",
    "model",
    "status",
    "duration_ms",
    "memory_persisted",
    "error_category",
)


def empty_evaluation() -> dict[str, int | float]:
    """
    Return the deterministic summary for an empty audit state.
    """

    return {
        "total_executions": 0,
        "success_count": 0,
        "failure_count": 0,
        "timeout_count": 0,
        "blocked_count": 0,
        "average_duration_ms": 0.0,
        "success_rate": 0.0,
        "memory_persistence_count": 0,
        "memory_persistence_rate": 0.0,
    }


def load_audit_metadata(path: Path | None = None) -> list[dict[str, Any]]:
    """
    Load valid audit records while retaining only permitted metadata fields.
    """

    audit_path = path or AUDIT_LOG_PATH
    try:
        audit_exists = audit_path.exists()
    except OSError:
        return []

    if not audit_exists:
        return []

    records = []

    try:
        with audit_path.open("r", encoding="utf-8") as audit_file:
            for line in audit_file:
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue

                normalized = _normalize_audit_record(record)
                if normalized is not None:
                    records.append(normalized)
    except (OSError, UnicodeError):
        return []

    return records


def aggregate_runtime_evaluations(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, int | float]:
    """
    Aggregate valid runtime audit metadata into deterministic quality metrics.
    """

    summary = empty_evaluation()
    valid_records = []

    for record in records:
        normalized = _normalize_audit_record(record)
        if normalized is not None:
            valid_records.append(normalized)

    if not valid_records:
        return summary

    summary["total_executions"] = len(valid_records)

    for status in RUNTIME_STATUSES:
        summary[f"{status}_count"] = sum(
            record["status"] == status
            for record in valid_records
        )

    summary["average_duration_ms"] = (
        sum(record["duration_ms"] for record in valid_records)
        / len(valid_records)
    )
    summary["success_rate"] = (
        summary["success_count"] / len(valid_records)
    )
    summary["memory_persistence_count"] = sum(
        record["memory_persisted"]
        for record in valid_records
    )
    summary["memory_persistence_rate"] = (
        summary["memory_persistence_count"] / len(valid_records)
    )

    return summary


def evaluate_runtime(path: Path | None = None) -> dict[str, int | float]:
    """
    Evaluate the current runtime audit log on demand.
    """

    return aggregate_runtime_evaluations(load_audit_metadata(path))


def _normalize_audit_record(
    record: Mapping[str, Any] | Any,
) -> dict[str, Any] | None:
    if not isinstance(record, Mapping):
        return None

    status = record.get("status")
    duration_ms = record.get("duration_ms")
    memory_persisted = record.get("memory_persisted")

    if status not in RUNTIME_STATUSES:
        return None
    if (
        isinstance(duration_ms, bool)
        or not isinstance(duration_ms, (int, float))
        or not isfinite(duration_ms)
        or duration_ms < 0
    ):
        return None
    if not isinstance(memory_persisted, bool):
        return None

    return {
        field: record.get(field)
        for field in AUDIT_METADATA_FIELDS
    }
