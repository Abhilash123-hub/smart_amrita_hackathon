"""W3C PROV-O JSON-LD provenance generator."""

from datetime import datetime, timezone
from typing import Any, Optional
from traceai.schemas.asset import AssetInput


def build_prov_lineage(
    asset: AssetInput,
    status: str,
    matched_source: Optional[str] = None,
    similarity_score: Optional[float] = None,
    certificate_id: Optional[str] = None,
    activity_name: str = "TraceAI-Ingestion-Scan",
    reviewer_id: Optional[str] = None,
    jurisdiction: Optional[str] = None,
) -> dict[str, Any]:
    """Construct an extended W3C PROV-O compatible JSON-LD representation."""
    now_iso = datetime.now(timezone.utc).isoformat()
    
    activity_id = f"urn:traceai:activity:{activity_name}:{asset.sha256_hash.replace(':', '_')}"
    entity_id = f"urn:traceai:asset:{asset.sha256_hash}"

    activity_doc: dict[str, Any] = {
        "@id": activity_id,
        "@type": "prov:Activity",
        "prov:startedAtTime": asset.crawl_timestamp or now_iso,
        "prov:endedAtTime": now_iso,
        "prov:wasAssociatedWith": {
            "@type": "prov:Agent",
            "@id": "urn:traceai:agent:gateway-v0.1.0",
            "traceai:track": asset.track.value,
        },
        "traceai:resolutionStatus": status,
        "traceai:similarityScore": similarity_score,
        "traceai:matchedSource": matched_source,
        "traceai:certificateId": certificate_id,
    }

    # Additive web scrape provenance (A4)
    if asset.source_url:
        activity_doc["prov:source_url"] = asset.source_url
    if asset.http_headers:
        activity_doc["traceai:http_headers"] = {
            "content_type": asset.http_headers.get("content-type"),
            "last_modified": asset.http_headers.get("last-modified"),
            "license_header": asset.http_headers.get("x-license") or asset.http_headers.get("license"),
        }
    if asset.prefilter_decision:
        activity_doc["traceai:prefilter_decision"] = asset.prefilter_decision
    if asset.source_trust_tier:
        activity_doc["traceai:source_trust_tier"] = asset.source_trust_tier
    if reviewer_id:
        activity_doc["prov:wasAttributedTo"] = f"urn:traceai:reviewer:{reviewer_id}"
    if jurisdiction:
        activity_doc["traceai:jurisdiction"] = jurisdiction

    derived_from_doc: dict[str, Any] = {
        "@type": "prov:Entity",
        "@id": f"urn:traceai:file:{asset.asset_id}",
        "traceai:mimeType": asset.mime_type,
        "traceai:byteSize": asset.size_bytes,
    }
    if asset.source_url:
        derived_from_doc["prov:atLocation"] = asset.source_url

    prov_doc: dict[str, Any] = {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "traceai": "https://traceai.dev/ns/provenance#",
        },
        "@id": entity_id,
        "@type": "prov:Entity",
        "prov:wasDerivedFrom": derived_from_doc,
        "prov:wasGeneratedBy": activity_doc,
    }

    return prov_doc
