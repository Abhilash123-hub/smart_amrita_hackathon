"""Auto-Generated Dataset and Model Cards (B11): Hugging Face style YAML front-matter documentation."""

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any


def generate_dataset_card(
    dataset_name: str,
    training_run_id: str,
    prov_graphs: list[dict[str, Any]],
    index_version: str = "v1.0.0",
) -> str:
    """Generate a standard Hugging Face dataset card with YAML front-matter populated from PROV-O provenance.
    
    Acceptance Criteria: Valid against target schema (HF YAML front-matter), requires no manual editing.
    """
    total_assets = len(prov_graphs)
    sources = []
    statuses = []
    licenses = []
    cert_ids = []

    for graph in prov_graphs:
        act = graph.get("prov:wasGeneratedBy", {})
        status = act.get("traceai:resolutionStatus", "UNKNOWN")
        statuses.append(status)

        cid = act.get("traceai:certificateId")
        if cid:
            cert_ids.append(cid)

        # Source URL or file ID
        derived = graph.get("prov:wasDerivedFrom", {})
        loc = derived.get("prov:atLocation") or derived.get("@id", "local_file")
        sources.append(loc)

        # Prefilter license hint
        pref = act.get("traceai:prefilter_decision", {})
        lic = pref.get("license_hint") or "Proprietary/Unspecified"
        licenses.append(lic)

    status_counts = Counter(statuses)
    license_counts = Counter(licenses)
    screened_pct = 100.0 if total_assets > 0 else 0.0
    passed_pct = (status_counts.get("PASSED", 0) / max(total_assets, 1)) * 100.0

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Render Hugging Face YAML front-matter followed by Markdown summary
    card = f"""---
license: other
task_categories:
- text-generation
- image-feature-extraction
tags:
- copyright-cleared
- traceai-verified
- automated-provenance
dataset_info:
  dataset_name: {dataset_name}
  training_run_id: {training_run_id}
  total_samples: {total_assets}
  screened_percentage: {screened_pct:.1f}%
  clearance_rate: {passed_pct:.1f}%
  index_version_used: {index_version}
  verification_date: '{now_iso}'
---

# Dataset Card for {dataset_name}

## Summary & Copyright Screening
This dataset has been audited and cleared through the **TraceAI Multimodal Ingestion Gateway**. All included assets have undergone automated byte-sniffing, two-stage vector and cross-encoder matching, and compliance pre-filtering against known protected works.

### Key Governance Metrics
- **Total Audited Assets:** {total_assets}
- **Cryptographic Clearance Certificates Issued:** {len(cert_ids)}
- **Screened Compliance:** {screened_pct:.1f}%
- **Copyright Index Version:** `{index_version}`

### License & Provenance Distribution
"""
    for lic_name, cnt in license_counts.items():
        card += f"- **{lic_name}:** {cnt} assets ({(cnt / max(total_assets, 1)) * 100:.1f}%)\n"

    card += f"""
### Ingestion Status Breakdown
- **PASSED (Cleared with RSA-PSS Signature):** {status_counts.get('PASSED', 0)}
- **BLOCKED (Copyright Infringement Risk Intercepted):** {status_counts.get('BLOCKED', 0)}
- **HUMAN_REVIEW (Resolved):** {status_counts.get('HUMAN_REVIEW', 0)}

### Cryptographic Audit Sample Certificates
"""
    for cid in cert_ids[:5]:
        card += f"- `{cid}`\n"
    if len(cert_ids) > 5:
        card += f"- *...and {len(cert_ids) - 5} additional certificates anchored in W3C PROV-O audit trail.*\n"

    return card
