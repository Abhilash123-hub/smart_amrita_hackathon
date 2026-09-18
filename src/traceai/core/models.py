"""Frozen Pydantic Schema Contracts for TraceAI (Task Card T0.2)."""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class Track(str, Enum):
    """Supported inspection tracks."""
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class Verdict(str, Enum):
    """Gateway inspection verdicts."""
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"


class AssetInput(BaseModel):
    """Input asset representation for gateway ingestion."""
    asset_id: str = Field(min_length=1, max_length=256)
    source_uri: str
    declared_license: str | None = None  # untrusted hint only
    mime_type: Literal[
        "text/plain",
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/webp"
    ]


class IngestRequest(BaseModel):
    """Ingestion batch request schema."""
    batch_id: str = Field(min_length=3, max_length=128)
    assets: list[AssetInput] = Field(min_length=1, max_length=10_000)


class ScanResult(BaseModel):
    """Per-asset inspection verdict and telemetry."""
    asset_id: str
    track: Track
    verdict: Verdict
    score: float = Field(ge=0.0, le=1.0)
    matched_source: str | None = None
    asset_hash: str  # "sha256:<64 hex>"
    evidence_uri: str | None = None
    scanned_at: datetime

    @field_validator("asset_hash")
    @classmethod
    def _hash_shape(cls, v: str) -> str:
        prefix, _, digest = v.partition(":")
        if (
            prefix != "sha256"
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("asset_hash must be sha256:<64 lowercase hex>")
        return v


class ClearanceCertificate(BaseModel):
    """Cryptographically signed clearance certificate for PASSED assets."""
    certificate_id: UUID
    asset_id: str
    asset_hash: str
    verdict: Literal[Verdict.PASSED]
    issued_at: datetime
    rsa_signature: str  # hex, PSS over canonical JSON


class EvidenceRecord(BaseModel):
    """Tamper-evident record for quarantined BLOCKED assets."""
    asset_id: str
    asset_hash: str
    matched_source: str
    score: float
    crop_uri: str | None = None   # image track
    text_span: str | None = None  # text track
    locked_at: datetime
