from __future__ import annotations

"""TRACEAI Data Layer Integration Service (Member 4 - Task C).

Connects the completed data layer (data/sample/sample_sources.json,
data/dataset_manifest.json, and sample assets) to the Backend and AI pipelines.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SAMPLE_DIR = DATA_DIR / "sample"
SOURCES_JSON = SAMPLE_DIR / "sample_sources.json"
MANIFEST_JSON = DATA_DIR / "dataset_manifest.json"


class DataService:
    """Core integration service connecting the Data Layer to Backend and AI layers."""

    def __init__(self, data_dir: Optional[Path | str] = None):
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.sample_dir = self.data_dir / "sample"
        self.sources_json = self.sample_dir / "sample_sources.json"
        self.manifest_json = self.data_dir / "dataset_manifest.json"
        self._records_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._manifest_cache: Optional[Dict[str, Any]] = None

    def load_records(self, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """Load and cache provenance records from data/sample/sample_sources.json."""
        if self._records_cache is not None and not force_reload:
            return self._records_cache

        if not self.sources_json.exists():
            raise FileNotFoundError(f"Provenance metadata not found: {self.sources_json}")

        with open(self.sources_json, "r", encoding="utf-8") as f:
            raw_records = json.load(f)

        records = {}
        for r in raw_records:
            records[r["record_id"]] = r

        self._records_cache = records
        return self._records_cache

    def load_manifest(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load dataset manifest from data/dataset_manifest.json."""
        if self._manifest_cache is not None and not force_reload:
            return self._manifest_cache

        if not self.manifest_json.exists():
            raise FileNotFoundError(f"Dataset manifest not found: {self.manifest_json}")

        with open(self.manifest_json, "r", encoding="utf-8") as f:
            self._manifest_cache = json.load(f)

        return self._manifest_cache

    def list_records(self, record_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sample records, optionally filtered by type (text/image)."""
        records = self.load_records()
        result = list(records.values())
        if record_type:
            result = [r for r in result if r.get("record_type") == record_type]
        return result

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific record by its record_id."""
        records = self.load_records()
        return records.get(record_id)

    def resolve_file_path(self, record: Dict[str, Any]) -> Path:
        """Resolve absolute file path for a record."""
        rel_path = record.get("file_path", "")
        abs_path = REPO_ROOT / rel_path
        if abs_path.exists():
            return abs_path
        if record.get("record_type") == "text":
            fallback = self.sample_dir / "documents" / record.get("file_name", "")
        else:
            fallback = self.sample_dir / "images" / record.get("file_name", "")
        if fallback.exists():
            return fallback
        return abs_path

    # -------------------------------------------------------------
    # Identity Signal: Exact SHA-256 Hashing
    # -------------------------------------------------------------
    @staticmethod
    def compute_sha256(file_path: Union[Path, str]) -> str:
        """Compute SHA-256 from actual file bytes. Format: 'sha256:<hex>'."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Cannot compute hash: file does not exist: {path}")

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return f"sha256:{hasher.hexdigest()}"

    @staticmethod
    def compute_sha256_bytes(data: bytes) -> str:
        """Compute SHA-256 from raw bytes."""
        return f"sha256:{hashlib.sha256(data).hexdigest()}"

    # -------------------------------------------------------------
    # Visual Signal: Image Perceptual Hash (pHash)
    # -------------------------------------------------------------
    @staticmethod
    def compute_phash(file_path: Union[Path, str]) -> Optional[str]:
        """Compute perceptual hash (pHash) for image records using PIL and ImageHash."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Cannot compute pHash: file does not exist: {path}")

        try:
            import imagehash
            from PIL import Image

            with Image.open(path) as img:
                h = imagehash.phash(img)
                return str(h)
        except Exception as e:
            logger.warning("Could not compute pHash for %s: %s", path, e)
            return None

    # -------------------------------------------------------------
    # Semantic Similarity Search
    # -------------------------------------------------------------
    def search_similarity(
        self,
        query_text: Optional[str] = None,
        query_file: Optional[Path | str] = None,
        record_type: str = "text",
        target_records: Optional[List[Dict[str, Any]]] = None,
        exclude_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search similarity across the dataset without fabricating scores."""
        records = self.load_records()
        candidates = []
        pool = target_records if target_records is not None else list(records.values())

        if record_type == "text":
            import re

            if query_text is None and query_file:
                qp = Path(query_file)
                if qp.exists():
                    query_text = qp.read_text(encoding="utf-8")
                else:
                    return []

            if not query_text:
                return []

            def clean_tokens(s: str) -> set[str]:
                return set(re.findall(r"\b\w{3,}\b", s.lower()))

            q_tokens = clean_tokens(query_text)

            for rec in pool:
                rec_id = rec.get("record_id")
                if rec.get("record_type") != "text" or rec_id == exclude_id:
                    continue
                fp = self.resolve_file_path(rec)
                if not fp.exists():
                    continue

                ref_text = fp.read_text(encoding="utf-8")
                ref_tokens = clean_tokens(ref_text)
                if not ref_tokens:
                    continue

                # Jaccard and directional overlap
                intersection = len(q_tokens & ref_tokens)
                jaccard = intersection / max(len(q_tokens | ref_tokens), 1)
                overlap = intersection / max(len(ref_tokens), 1)
                seq_ratio = SequenceMatcher(None, query_text.lower(), ref_text.lower()).ratio()

                # For near-duplicate detection, overlap and sequence ratio identify derivation
                sim_score = max(seq_ratio, (overlap * 0.7 + jaccard * 0.3))

                if sim_score > 0.05:
                    candidates.append({
                        "record_id": rec_id,
                        "file_name": rec.get("file_name"),
                        "similarity": round(sim_score, 4),
                        "similarity_type": "lexical_semantic",
                        "parent_relationship": rec.get("parent_record") == exclude_id or rec_id == records.get(exclude_id or "", {}).get("parent_record"),
                    })

        elif record_type == "image":
            import imagehash
            import numpy as np
            from PIL import Image

            if not query_file or not Path(query_file).exists():
                return []

            try:
                with Image.open(query_file) as qimg:
                    q_phash = imagehash.phash(qimg)
                    q_thumb = np.array(qimg.convert("L").resize((64, 64)), dtype=np.float32) / 255.0
            except Exception as e:
                logger.warning("Failed to hash query image: %s", e)
                return []

            for rec in pool:
                rec_id = rec.get("record_id")
                if rec.get("record_type") != "image" or rec_id == exclude_id:
                    continue
                fp = self.resolve_file_path(rec)
                if not fp.exists():
                    continue

                try:
                    with Image.open(fp) as ref_img:
                        ref_phash = imagehash.phash(ref_img)
                        ref_thumb = np.array(ref_img.convert("L").resize((64, 64)), dtype=np.float32) / 255.0

                    hamming_dist = q_phash - ref_phash
                    phash_sim = 1.0 - (hamming_dist / 64.0)

                    # Normalized visual cosine similarity
                    q_norm = np.linalg.norm(q_thumb.flatten())
                    r_norm = np.linalg.norm(ref_thumb.flatten())
                    cos_sim = float(np.dot(q_thumb.flatten(), ref_thumb.flatten()) / (q_norm * r_norm))

                    # Composite image similarity
                    sim_score = (phash_sim * 0.4) + (cos_sim * 0.6)

                    candidates.append({
                        "record_id": rec_id,
                        "file_name": rec.get("file_name"),
                        "similarity": round(max(0.0, sim_score), 4),
                        "hamming_distance": hamming_dist,
                        "similarity_type": "phash_visual_embedding",
                        "parent_relationship": rec.get("parent_record") == exclude_id or rec_id == records.get(exclude_id or "", {}).get("parent_record"),
                    })
                except Exception as e:
                    logger.debug("Failed comparing image %s: %s", fp, e)

        candidates.sort(key=lambda c: c["similarity"], reverse=True)
        return candidates

    # -------------------------------------------------------------
    # Provenance Graph & Lineage
    # -------------------------------------------------------------
    def get_provenance(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Construct a structured W3C PROV-O-compatible lineage DAG."""
        rec = self.get_record(record_id)
        if not rec:
            return None

        lineage_chain = [
            {"step": 1, "entity": "Source", "label": rec.get("source"), "type": rec.get("source_type"), "url": rec.get("source_url")},
            {"step": 2, "entity": "Dataset", "label": rec.get("dataset"), "version": rec.get("dataset_version"), "license": rec.get("license")},
        ]

        parent_id = rec.get("parent_record")
        if parent_id:
            parent_rec = self.get_record(parent_id)
            lineage_chain.append({
                "step": 3,
                "entity": "Parent Record",
                "record_id": parent_id,
                "file_name": parent_rec.get("file_name") if parent_rec else None,
            })
            lineage_chain.append({
                "step": 4,
                "entity": "Transformation",
                "description": rec.get("transformation"),
            })
            lineage_chain.append({
                "step": 5,
                "entity": "Derived Record",
                "record_id": record_id,
                "file_name": rec.get("file_name"),
            })
        else:
            lineage_chain.append({
                "step": 3,
                "entity": "Transformation",
                "description": rec.get("transformation"),
            })
            lineage_chain.append({
                "step": 4,
                "entity": "Target Record",
                "record_id": record_id,
                "file_name": rec.get("file_name"),
            })

        required_fields = ["record_id", "file_name", "record_type", "source", "source_type", "license", "dataset", "dataset_version", "transformation"]
        present_count = sum(1 for f in required_fields if rec.get(f))
        completeness_pct = round((present_count / len(required_fields)) * 100, 1)

        return {
            "record_id": record_id,
            "dataset": rec.get("dataset"),
            "dataset_version": rec.get("dataset_version"),
            "source": rec.get("source"),
            "source_type": rec.get("source_type"),
            "source_url": rec.get("source_url"),
            "license": rec.get("license"),
            "license_verified": rec.get("license_verified", False),
            "transformation": rec.get("transformation"),
            "parent_record": parent_id,
            "lineage_chain": lineage_chain,
            "provenance_completeness": completeness_pct,
        }

    # -------------------------------------------------------------
    # Transparent Risk / Review Indicator Calculation
    # -------------------------------------------------------------
    @staticmethod
    def calculate_review_indicator(
        similarity_score: float,
        license_verified: bool,
        source_type: Optional[str] = "synthetic",
        parent_record: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate a transparent review indicator from concrete input signals.

        Inputs:
          - similarity_score (S in [0, 1])
          - license_verified (boolean)
          - source_type (string)
          - parent_record (optional)

        Formula:
          CompositeRisk = S + (0.35 if not license_verified else 0.0) + (0.20 if source_type in ['scraped', 'unknown'] else 0.0)

        Thresholds:
          - CompositeRisk < 0.40 -> LOW (Low provenance risk — reference / clean record)
          - 0.40 <= CompositeRisk < 0.75 -> MEDIUM (Moderate provenance risk — partial similarity, human review recommended)
          - CompositeRisk >= 0.75 -> HIGH (Potential provenance risk — provenance & licence review required before AI training use)

        IMPORTANT:
          These are REVIEW CATEGORIES to guide human assessment, NOT legal determinations.
        """
        lic_penalty = 0.35 if not license_verified else 0.0
        src_penalty = 0.20 if source_type in ["scraped", "unknown"] else 0.0
        
        composite_score = similarity_score + lic_penalty + src_penalty

        if composite_score < 0.40:
            category = "LOW"
            status = "Low provenance risk — reference / clean record. Cleared for standard review."
        elif composite_score < 0.75:
            category = "MEDIUM"
            status = "Moderate provenance risk — partial similarity detected. Human review recommended."
        else:
            category = "HIGH"
            status = "Potential provenance risk — high similarity or unverified lineage. Provenance & licence review required before AI training use."

        return {
            "review_indicator": category,
            "composite_risk_score": round(composite_score, 4),
            "review_status": status,
            "formula": "CompositeRisk = MaxSimilarity + LicencePenalty + SourceRisk",
            "breakdown": {
                "max_similarity": round(similarity_score, 4),
                "licence_verified": license_verified,
                "licence_penalty": lic_penalty,
                "source_type": source_type,
                "source_penalty": src_penalty,
            },
        }

    # -------------------------------------------------------------
    # Full End-to-End Analysis Workflow
    # -------------------------------------------------------------
    def analyze_record(self, record_id: str) -> Dict[str, Any]:
        """Execute full end-to-end trace for a record from data/sample."""
        rec = self.get_record(record_id)
        if not rec:
            raise KeyError(f"Record '{record_id}' not found in dataset.")

        fp = self.resolve_file_path(rec)
        if not fp.exists():
            raise FileNotFoundError(f"File for record '{record_id}' not found at: {fp}")

        # 1. Identity Signal: SHA-256
        sha256_hash = self.compute_sha256(fp)

        # 2. Visual Signal: pHash (if image)
        phash_val = self.compute_phash(fp) if rec.get("record_type") == "image" else None

        # 3. Similarity Search
        rec_type = rec.get("record_type", "text")
        parent_id = rec.get("parent_record")

        # If the record has a parent in the dataset, compute derivation similarity against the parent
        if parent_id:
            parent_rec = self.get_record(parent_id)
            if parent_rec:
                candidates = self.search_similarity(
                    query_file=fp,
                    record_type=rec_type,
                    target_records=[parent_rec],
                )
            else:
                candidates = []
        else:
            # Root reference record — independent baseline, no parent derivation risk
            candidates = []

        max_sim = candidates[0]["similarity"] if candidates else 0.0

        # 4. Provenance & Lineage
        prov = self.get_provenance(record_id) or {}

        # 5. Review Indicator Calculation
        review = self.calculate_review_indicator(
            similarity_score=max_sim,
            license_verified=rec.get("license_verified", True),
            source_type=rec.get("source_type", "synthetic"),
            parent_record=parent_id,
            notes=rec.get("notes"),
        )

        return {
            "record_id": record_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "record_type": rec_type,
            "file_name": rec.get("file_name"),
            "file_path": rec.get("file_path"),
            "sha256": sha256_hash,
            "phash": phash_val,
            "source": rec.get("source"),
            "source_type": rec.get("source_type"),
            "source_url": rec.get("source_url"),
            "license": rec.get("license"),
            "license_verified": rec.get("license_verified", True),
            "dataset": rec.get("dataset"),
            "dataset_version": rec.get("dataset_version"),
            "transformation": rec.get("transformation"),
            "parent_record": parent_id,
            "lineage": prov.get("lineage_chain", []),
            "provenance_completeness": prov.get("provenance_completeness", 100.0),
            "similarity_results": candidates,
            "review_indicator": review["review_indicator"],
            "composite_risk_score": review["composite_risk_score"],
            "review_status": review["review_status"],
            "scoring_breakdown": review["breakdown"],
            "intended_demo_category": rec.get("similarity_demo_category"),
            "demo_note": rec.get("similarity_demo_note"),
        }

    # -------------------------------------------------------------
    # Audit Evidence Export (JSON & HTML)
    # -------------------------------------------------------------
    def export_evidence(self, record_id: str, format: str = "json") -> Tuple[str, str]:
        """Export evidence package in JSON or HTML format. Returns (content, mime_type)."""
        data = self.analyze_record(record_id)

        if format.lower() == "json":
            return json.dumps(data, indent=2), "application/json"

        badge_color = {
            "LOW": "#10b981",
            "MEDIUM": "#f59e0b",
            "HIGH": "#ef4444",
        }.get(data["review_indicator"], "#6b7280")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TRACEAI Evidence Audit Report — {data['record_id']}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 40px; }}
    .container {{ max-width: 860px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; }}
    h1 {{ color: #ffffff; font-size: 24px; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }}
    .subtitle {{ color: #94a3b8; font-size: 14px; margin-bottom: 24px; }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; color: #fff; background: {badge_color}; }}
    .section {{ margin-top: 24px; border-top: 1px solid #1e293b; padding-top: 20px; }}
    .section-title {{ font-size: 14px; text-transform: uppercase; color: #38bdf8; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #1e293b; }}
    td.label {{ color: #94a3b8; font-weight: 600; width: 220px; }}
    .mono {{ font-family: "JetBrains Mono", Consolas, monospace; color: #34d399; word-break: break-all; }}
    .chain {{ background: #0f172a; border-radius: 8px; padding: 12px 16px; margin-top: 8px; }}
    .chain-step {{ padding: 6px 0; border-bottom: 1px dashed #334155; font-size: 13px; }}
    .chain-step:last-child {{ border-bottom: none; }}
    .footer {{ margin-top: 32px; text-align: center; font-size: 11px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>
      <span>TRACEAI Cryptographic Audit Record</span>
      <span class="badge">{data['review_indicator']} RISK</span>
    </h1>
    <div class="subtitle">Generated on {data['timestamp']} | Record: {data['record_id']}</div>

    <div class="section">
      <div class="section-title">1. Exact Cryptographic Identity</div>
      <table>
        <tr><td class="label">Record ID</td><td class="mono">{data['record_id']}</td></tr>
        <tr><td class="label">File Name</td><td>{data['file_name']}</td></tr>
        <tr><td class="label">SHA-256 Byte Hash</td><td class="mono">{data['sha256']}</td></tr>
        {f"<tr><td class='label'>Perceptual Hash (pHash)</td><td class='mono'>{data['phash']}</td></tr>" if data.get('phash') else ""}
      </table>
    </div>

    <div class="section">
      <div class="section-title">2. Provenance & Lineage Trail</div>
      <table>
        <tr><td class="label">Dataset</td><td>{data['dataset']} (v{data['dataset_version']})</td></tr>
        <tr><td class="label">Source Origin</td><td>{data['source']} ({data['source_type']})</td></tr>
        <tr><td class="label">Licence Declared</td><td>{data['license']} (Verified: {data['license_verified']})</td></tr>
        <tr><td class="label">Transformation Applied</td><td>{data['transformation']}</td></tr>
        <tr><td class="label">Parent Record</td><td>{data['parent_record'] or 'None (Root Record)'}</td></tr>
        <tr><td class="label">Provenance Completeness</td><td>{data['provenance_completeness']}%</td></tr>
      </table>

      <div class="chain">
        <strong style="color: #94a3b8; font-size: 12px;">W3C PROV-O Lineage DAG:</strong>
        {''.join(f"<div class='chain-step'>Step {s.get('step')}: <strong>{s.get('entity')}</strong> &rarr; {s.get('label') or s.get('record_id') or s.get('description')}</div>" for s in data.get('lineage', []))}
      </div>
    </div>

    <div class="section">
      <div class="section-title">3. Semantic Similarity & Risk Assessment</div>
      <table>
        <tr><td class="label">Review Indicator</td><td><strong>{data['review_indicator']}</strong></td></tr>
        <tr><td class="label">Composite Risk Score</td><td class="mono">{data['composite_risk_score']}</td></tr>
        <tr><td class="label">Assessment Summary</td><td>{data['review_status']}</td></tr>
      </table>
    </div>

    <div class="footer">
      TRACEAI Evidence-Traceability System | IP Cleanliness & AI Dataset Provenance<br>
      Note: This record provides technical provenance evidence to support human review and does not constitute a legal conclusion.
    </div>
  </div>
</body>
</html>
"""
        return html_content, "text/html"


# Default singleton instance
data_service = DataService()
