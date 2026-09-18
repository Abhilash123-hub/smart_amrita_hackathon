"""Confidence-Band Routing (B4): Tri-band decision routing and human review queue."""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from traceai.crypto.signer import CryptoSigner
from traceai.schemas.asset import AssetInput
from traceai.schemas.certificate import ClearanceCertificate
from traceai.schemas.report import AssetEvaluation, AssetStatus
from traceai.tracks.base import MatchResult
from traceai.web_ingestion.models import TrustTier

logger = logging.getLogger(__name__)


class ConfidenceBandRouter:
    """Routes matches into three confidence bands:
    
    score < LOW_THRESHOLD           -> CLEAR (auto-issue certificate)
    LOW_THRESHOLD <= score < HIGH   -> HUMAN_REVIEW (held in review queue)
    score >= HIGH_THRESHOLD         -> BLOCKED (auto-reject)
    """

    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        default_high_text: float = 0.85,
        default_high_image: float = 0.90,
    ):
        self.default_high_text = default_high_text
        self.default_high_image = default_high_image

        if db_path is None:
            data_dir = Path("./data").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "traceai_review_queue.db"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_queue (
                    asset_id TEXT PRIMARY KEY,
                    track TEXT NOT NULL,
                    score REAL NOT NULL,
                    matched_source TEXT,
                    asset_hash TEXT NOT NULL,
                    source_url TEXT,
                    trust_tier TEXT,
                    status TEXT NOT NULL,
                    reviewer_id TEXT,
                    resolution_notes TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_low_threshold(self, trust_tier: Optional[str], track: str) -> float:
        """Configurable per source trust_tier (A1) — tighter band for high-risk-domain sources."""
        tier = trust_tier or TrustTier.PUBLIC_WEB_UNKNOWN.value
        base_low = 0.70 if track == "TEXT" else 0.75

        if tier == TrustTier.HIGH_RISK_DOMAIN.value:
            # Tighter band: routes more mid-confidence items to human review
            return base_low - 0.15  # 0.55 / 0.60
        elif tier == TrustTier.LICENSED_PARTNER.value:
            # Relaxed band: trusted partner
            return base_low + 0.10  # 0.80 / 0.85
        return base_low  # 0.70 / 0.75

    def route_asset(
        self,
        asset: AssetInput,
        match: MatchResult,
        trust_tier: Optional[str] = None,
    ) -> tuple[str, AssetStatus]:
        """Determine band: (band_name, status).
        
        Returns: ("CLEAR" | "HUMAN_REVIEW" | "BLOCKED", AssetStatus)
        """
        score = match.similarity_score or 0.0
        high_threshold = self.default_high_image if asset.track.value == "IMAGE" else self.default_high_text
        low_threshold = self.get_low_threshold(trust_tier or asset.source_trust_tier, asset.track.value)

        if score >= high_threshold:
            return "BLOCKED", AssetStatus.BLOCKED
        elif score >= low_threshold:
            # Held pending human review (B4)
            self._enqueue_for_review(asset, match, score, trust_tier)
            return "HUMAN_REVIEW", AssetStatus.HUMAN_REVIEW
        else:
            return "CLEAR", AssetStatus.PASSED

    def _enqueue_for_review(
        self, asset: AssetInput, match: MatchResult, score: float, trust_tier: Optional[str]
    ):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO review_queue
                (asset_id, track, score, matched_source, asset_hash, source_url, trust_tier, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
                """,
                (
                    asset.asset_id,
                    asset.track.value,
                    score,
                    match.matched_source,
                    asset.sha256_hash,
                    asset.source_url,
                    trust_tier or asset.source_trust_tier,
                    now,
                ),
            )
            conn.commit()

    def get_pending_review_queue(self) -> list[dict]:
        """List assets awaiting human review for the UI Inspection Modal."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM review_queue WHERE status = 'PENDING' ORDER BY score DESC")
            return [dict(r) for r in cur.fetchall()]

    def resolve_review(
        self,
        asset_id: str,
        reviewer_id: str,
        approve: bool,
        notes: Optional[str] = None,
        signer: Optional[CryptoSigner] = None,
    ) -> dict:
        """Human reviewer resolves asset: Approve -> CLEAR; Reject -> BLOCKED.
        
        Logged into PROV-O as prov:wasAttributedTo: reviewer_id.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM review_queue WHERE asset_id = ?", (asset_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Asset {asset_id} not found in review queue")

            new_status = "APPROVED" if approve else "REJECTED"
            conn.execute(
                """
                UPDATE review_queue 
                SET status = ?, reviewer_id = ?, resolution_notes = ?
                WHERE asset_id = ?
                """,
                (new_status, reviewer_id, notes or "", asset_id),
            )
            conn.commit()

            certificate = None
            if approve and signer:
                certificate = signer.issue_certificate(asset_id, row["asset_hash"])
                certificate.human_reviewer_id = reviewer_id

            return {
                "asset_id": asset_id,
                "resolution": new_status,
                "reviewer_id": reviewer_id,
                "certificate": certificate.model_dump() if certificate else None,
                "prov_attribution": f"urn:traceai:reviewer:{reviewer_id}",
            }
