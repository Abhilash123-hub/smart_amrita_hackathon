"""Reporting schemas and output payload definitions for TraceAI."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from traceai.schemas.asset import TrackType
from traceai.schemas.certificate import ClearanceCertificate


class AssetStatus(str, Enum):
    """Clearance resolution status of an ingested asset."""
    PASSED = "PASSED"
    BLOCKED = "BLOCKED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ERROR = "ERROR"


class AssetEvaluation(BaseModel):
    """Evaluation result for a single ingested asset.
    
    Adheres strictly to the TraceAI output format:
    {
      "asset_id": "book_excerpt_0421.txt",
      "status": "BLOCKED",
      "track": "TEXT",
      "matched_source": "© O'Reilly Media",
      "similarity_score": 0.94,
      "asset_hash": "sha256:9f3c...e7a1",
      "certificate_id": null
    }
    """

    asset_id: str = Field(description="Unique asset identifier")
    status: AssetStatus = Field(description="Resolution status: PASSED or BLOCKED")
    track: TrackType = Field(description="Processing track: TEXT or IMAGE")
    matched_source: Optional[str] = Field(
        default=None,
        description="Identified copyrighted source if flagged; null if clean",
    )
    similarity_score: Optional[float] = Field(
        default=None,
        description="Highest matching similarity score; null if clean",
    )
    asset_hash: str = Field(description="SHA-256 byte hash with 'sha256:' prefix")
    certificate_id: Optional[str] = Field(
        default=None,
        description="UUID of cryptographic clearance certificate if PASSED; null if BLOCKED",
    )
    # Extended metadata attached for provenance & cryptographic verification
    certificate: Optional[ClearanceCertificate] = Field(
        default=None,
        description="Full cryptographic certificate when asset passes",
    )
    lineage: Optional[dict[str, Any]] = Field(
        default=None,
        description="W3C PROV-O JSON-LD lineage graph",
    )
    details: Optional[str] = Field(
        default=None,
        description="Additional debug or stage match diagnostics",
    )
    risk_band: Optional[str] = Field(
        default=None,
        description="Confidence band: CLEAR, HUMAN_REVIEW, or BLOCKED",
    )

    def to_minimal_dict(self) -> dict[str, Any]:
        """Export the exact minimal JSON structure required by TraceAI spec."""
        return {
            "asset_id": self.asset_id,
            "status": self.status.value,
            "track": self.track.value,
            "matched_source": self.matched_source,
            "similarity_score": self.similarity_score,
            "asset_hash": self.asset_hash,
            "certificate_id": self.certificate_id,
        }


class ScanSummary(BaseModel):
    """Aggregate statistical summary for a batch scan."""

    total_assets: int = 0
    passed_count: int = 0
    blocked_count: int = 0
    review_count: int = 0
    error_count: int = 0
    duration_seconds: float = 0.0


class ScanReport(BaseModel):
    """Complete batch scan report output."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Scan completion UTC timestamp",
    )
    input_directory: str
    index_directory: Optional[str] = None
    summary: ScanSummary
    results: list[AssetEvaluation] = Field(default_factory=list)

    def to_output_payload(self, minimal: bool = False) -> dict[str, Any]:
        """Produce final output payload."""
        if minimal:
            return {
                "summary": self.summary.model_dump(),
                "assets": [r.to_minimal_dict() for r in self.results],
            }
        return self.model_dump(mode="json")
