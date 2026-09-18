"""Content-Addressed Write-Once Evidence Locker (Task Card T2.2)."""

import json
from pathlib import Path
from typing import Any, Optional
from PIL import Image

from src.traceai.config import DEFAULT_CONFIG, GatewayConfig
from src.traceai.core.models import EvidenceRecord


class EvidenceLocker:
    """Content-addressed, immutable WORM (Write Once, Read Many) evidence vault.
    
    Structure: <base_path>/evidence/<asset_hash[:2]>/<asset_hash>/
      - metadata.json: Match details, score, timestamps
      - evidence_crop.png: Side-by-side composite proof (image track)
      - text_span.txt: Quoted copyrighted sequence (text track)
    """

    def __init__(self, root_dir: Optional[Path | str] = None, retention_days: int = 730):
        self.root_dir = Path(root_dir or DEFAULT_CONFIG.evidence_locker_root)
        self.retention_days = retention_days  # Default 24 months (730 days) retention

    def _get_vault_dir(self, asset_hash: str) -> Path:
        """Compute 2-level directory tree based on hash prefix."""
        # e.g. sha256:abc123... -> prefix = "ab"
        digest = asset_hash.partition(":")[2] if ":" in asset_hash else asset_hash
        prefix = digest[:2].lower()
        return self.root_dir / prefix / digest.lower()

    def store_evidence(
        self,
        record: EvidenceRecord,
        composite_crop: Optional[Image.Image] = None,
    ) -> str:
        """Store evidence bundle immutably. Raises FileExistsError if already exists."""
        vault_dir = self._get_vault_dir(record.asset_hash)

        if vault_dir.exists():
            raise FileExistsError(
                f"WORM Violation: Evidence for {record.asset_hash} is already locked and immutable."
            )

        vault_dir.mkdir(parents=True, exist_ok=False)

        # 1. Store metadata
        meta_file = vault_dir / "metadata.json"
        meta_file.write_text(record.model_dump_json(indent=2), encoding="utf-8")

        # 2. Store composite crop if available
        if composite_crop is not None:
            crop_path = vault_dir / "evidence_crop.png"
            composite_crop.save(crop_path, format="PNG")

        # 3. Store text span if present
        if record.text_span:
            span_path = vault_dir / "text_span.txt"
            span_path.write_text(record.text_span, encoding="utf-8")

        return str(meta_file)

    def retrieve_evidence(self, asset_hash: str) -> Optional[dict[str, Any]]:
        """Retrieve stored evidence bundle by asset hash."""
        vault_dir = self._get_vault_dir(asset_hash)
        meta_file = vault_dir / "metadata.json"
        if not meta_file.exists():
            return None

        data = json.loads(meta_file.read_text(encoding="utf-8"))
        crop_path = vault_dir / "evidence_crop.png"
        span_path = vault_dir / "text_span.txt"

        return {
            "record": EvidenceRecord.model_validate(data),
            "crop_path": str(crop_path) if crop_path.exists() else None,
            "text_span_path": str(span_path) if span_path.exists() else None,
            "vault_dir": str(vault_dir),
            "retention_days": self.retention_days,
        }
