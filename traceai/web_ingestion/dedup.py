from __future__ import annotations

"""Change-Aware Dedup (A5): Pre-fingerprint cost gate bypassing Stage 2 for previously seen assets."""

import hashlib
import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional

from traceai.schemas.asset import AssetInput, TrackType
from traceai.schemas.report import AssetStatus

logger = logging.getLogger(__name__)


def compute_simhash(text: str, bits: int = 64) -> int:
    """Compute 64-bit SimHash over tokenized text."""
    tokens = re.findall(r"\b\w{3,}\b", text.lower())
    if not tokens:
        return 0

    v = [0] * bits
    for token in tokens:
        # MD5 token hash
        t_hash = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        for i in range(bits):
            bit = (t_hash >> i) & 1
            if bit:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(bits):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def simhash_similarity(h1: int, h2: int, bits: int = 64) -> float:
    """Compute normalized bit similarity between two 64-bit SimHashes."""
    xor = h1 ^ h2
    hamming_dist = bin(xor).count("1")
    return 1.0 - (hamming_dist / bits)


class ChangeAwareDedup:
    """Cost gate preventing redundant Stage 2 invocations for duplicates of previously processed assets."""

    def __init__(self, db_path: Optional[Path | str] = None, text_threshold: float = 0.95, image_threshold: float = 0.95):
        self.text_threshold = text_threshold
        self.image_threshold = image_threshold
        self.stage2_skips = 0

        if db_path is None:
            data_dir = Path("./data").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "traceai_dedup.db"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingested_signatures (
                    asset_id TEXT,
                    sha256_hash TEXT PRIMARY KEY,
                    track TEXT NOT NULL,
                    status TEXT NOT NULL,
                    signature_val TEXT NOT NULL,
                    certificate_id TEXT,
                    matched_source TEXT
                )
                """
            )
            conn.commit()

    def record_evaluation(
        self,
        asset: AssetInput,
        status: AssetStatus,
        certificate_id: Optional[str] = None,
        matched_source: Optional[str] = None,
    ):
        """Save asset signature and resolution status for downstream dedup."""
        sig_str = ""
        if asset.track == TrackType.TEXT or asset.track == TrackType.CODE:
            text = asset.read_text()
            sig_val = compute_simhash(text)
            sig_str = str(sig_val)
        elif asset.track == TrackType.IMAGE:
            import imagehash
            from PIL import Image
            try:
                with Image.open(asset.file_path) as img:
                    sig_val = str(imagehash.phash(img))
                    sig_str = sig_val
            except Exception:
                sig_str = ""

        if not sig_str:
            return

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ingested_signatures
                (asset_id, sha256_hash, track, status, signature_val, certificate_id, matched_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.asset_id,
                    asset.sha256_hash,
                    asset.track.value,
                    status.value,
                    sig_str,
                    certificate_id,
                    matched_source,
                ),
            )
            conn.commit()

    def check_dedup(
        self, asset: AssetInput
    ) -> tuple[bool, Optional[AssetStatus], Optional[str], Optional[str], Optional[float]]:
        """Check if asset matches a previously cleared or blocked asset.
        
        Returns: (is_duplicate, prior_status, certificate_id, matched_source, similarity)
        """
        # 1. Exact SHA-256 match
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "SELECT status, certificate_id, matched_source FROM ingested_signatures WHERE sha256_hash = ?",
                (asset.sha256_hash,),
            )
            row = cur.fetchone()
            if row:
                self.stage2_skips += 1
                return True, AssetStatus(row[0]), row[1], row[2], 1.0

        # 2. Text / Code SimHash match
        if asset.track == TrackType.TEXT or asset.track == TrackType.CODE:
            text = asset.read_text()
            query_simhash = compute_simhash(text)
            if query_simhash == 0:
                return False, None, None, None, None

            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "SELECT status, signature_val, certificate_id, matched_source FROM ingested_signatures WHERE track = ?",
                    (asset.track.value,),
                )
                for status_val, sig_str, cert_id, matched_src in cur.fetchall():
                    try:
                        ref_simhash = int(sig_str)
                        sim = simhash_similarity(query_simhash, ref_simhash)
                        if sim >= self.text_threshold:
                            self.stage2_skips += 1
                            logger.info("A5 Dedup hit (text SimHash %s >= %s): bypassing Stage 2", sim, self.text_threshold)
                            return True, AssetStatus(status_val), cert_id, matched_src, round(sim, 4)
                    except ValueError:
                        pass

        # 3. Image pHash match
        elif asset.track == TrackType.IMAGE:
            import imagehash
            from PIL import Image
            try:
                with Image.open(asset.file_path) as img:
                    query_phash = imagehash.phash(img)
            except Exception:
                return False, None, None, None, None

            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "SELECT status, signature_val, certificate_id, matched_source FROM ingested_signatures WHERE track = ?",
                    (asset.track.value,),
                )
                for status_val, sig_str, cert_id, matched_src in cur.fetchall():
                    try:
                        ref_phash = imagehash.hex_to_hash(sig_str)
                        diff = query_phash - ref_phash
                        sim = 1.0 - (diff / 64.0)
                        if sim >= self.image_threshold:
                            self.stage2_skips += 1
                            logger.info("A5 Dedup hit (image pHash %s >= %s): bypassing Stage 2", sim, self.image_threshold)
                            return True, AssetStatus(status_val), cert_id, matched_src, round(sim, 4)
                    except Exception:
                        pass

        return False, None, None, None, None
