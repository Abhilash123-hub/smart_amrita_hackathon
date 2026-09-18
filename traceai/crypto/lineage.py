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
) -> dict[str, Any]:
    """Construct a minimal W3C PROV-O compatible JSON-LD representation."""
    now_iso = datetime.now(timezone.utc).isoformat()
    
    activity_id = f"urn:traceai:activity:{activity_name}:{asset.sha256_hash.replace(':', '_')}"
    entity_id = f"urn:traceai:asset:{asset.sha256_hash}"

    prov_doc: dict[str, Any] = {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "traceai": "https://traceai.dev/ns/provenance#",
        },
        "@id": entity_id,
        "@type": "prov:Entity",
        "prov:wasDerivedFrom": {
            "@type": "prov:Entity",
            "@id": f"urn:traceai:file:{asset.asset_id}",
            "traceai:mimeType": asset.mime_type,
            "traceai:byteSize": asset.size_bytes,
        },
        "prov:wasGeneratedBy": {
            "@id": activity_id,
            "@type": "prov:Activity",
            "prov:startedAtTime": now_iso,
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
        },
    }

    return prov_doc
