"""CI/CD & Data-Lake Connectors (B9): S3/GCS bucket events and ML Training Gatekeeper."""

import json
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ManifestItem(BaseModel):
    asset_id: str
    asset_hash: str


class TrainingManifest(BaseModel):
    training_run_id: str
    model_name: str
    manifest_assets: list[ManifestItem]


class CiCdGateResult(BaseModel):
    status: str  # "PASS" or "FAIL"
    total_manifest_assets: int
    cleared_count: int
    unresolved_count: int
    offending_assets: list[dict[str, Any]]
    message: str


class CiCdGatekeeper:
    """Pre-training CI/CD Gate ensuring training jobs cannot proceed with uncleared or blocked assets."""

    def __init__(self, clearance_registry: Optional[dict[str, str]] = None):
        # Map of sha256_hash -> status (PASSED, BLOCKED, HUMAN_REVIEW)
        self.clearance_registry: dict[str, str] = clearance_registry or {}

    def register_cleared_hash(self, asset_hash: str, status: str = "PASSED"):
        self.clearance_registry[asset_hash] = status

    def evaluate_manifest(self, manifest: TrainingManifest) -> CiCdGateResult:
        """Validate an entire training run dataset manifest.
        
        Acceptance Criteria: Training pipeline CI fails and reports specific offending
        assets when manifest includes any non-CLEAR asset.
        """
        offending = []
        cleared = 0

        for item in manifest.manifest_assets:
            status = self.clearance_registry.get(item.asset_hash)

            if status == "PASSED":
                cleared += 1
            else:
                offending.append({
                    "asset_id": item.asset_id,
                    "asset_hash": item.asset_hash,
                    "status": status or "UNAUDITED",
                    "reason": "Missing cryptographic clearance certificate" if not status else f"Asset marked as {status}",
                })

        is_pass = (len(offending) == 0)
        return CiCdGateResult(
            status="PASS" if is_pass else "FAIL",
            total_manifest_assets=len(manifest.manifest_assets),
            cleared_count=cleared,
            unresolved_count=len(offending),
            offending_assets=offending,
            message="All dataset assets possess valid cryptographic clearance." if is_pass else f"Build failed: {len(offending)} non-cleared assets identified.",
        )


class DataLakeBucketConnector:
    """Event-driven listener for S3/GCS bucket-create and Snowflake stage events."""

    def __init__(self):
        self.events_received: list[dict[str, Any]] = []

    def handle_s3_event(self, event_payload: dict[str, Any]) -> dict[str, Any]:
        """Simulate event-driven S3 ObjectCreated handler."""
        records = event_payload.get("Records", [])
        ingested = []
        for r in records:
            bucket = r.get("s3", {}).get("bucket", {}).get("name")
            key = r.get("s3", {}).get("object", {}).get("key")
            ingested.append({"bucket": bucket, "key": key, "action": "QUEUED_FOR_SCAN"})
            self.events_received.append({"type": "s3:ObjectCreated", "bucket": bucket, "key": key})
        return {"status": "INGESTION_TRIGGERED", "objects": ingested}
