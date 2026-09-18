"""W3C PROV-O Lineage Graph Generation and Projection (Task Card T2.4)."""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from src.traceai.core.models import ScanResult, Verdict


def extract_source_domain(source_uri: str) -> str:
    """Extract domain from URL or default to local filesystem path."""
    if "://" in source_uri:
        parsed = urlparse(source_uri)
        return parsed.netloc or "unknown"
    return "local-filesystem"


def build_prov_o_jsonld(
    result: ScanResult,
    source_uri: str,
    pipeline_version: str = "0.1.0",
    certificate_id: Optional[str] = None,
) -> dict[str, Any]:
    """Generate W3C PROV-O JSON-LD document describing the scan lineage."""
    domain = extract_source_domain(source_uri)
    asset_uri = f"urn:traceai:asset:{result.asset_hash}"
    activity_uri = f"urn:traceai:activity:scan:{result.asset_id}"
    agent_uri = f"urn:traceai:agent:engine:v{pipeline_version}"
    now_iso = datetime.now(timezone.utc).isoformat()

    graph = [
        # 1. Entity: Raw Asset
        {
            "@id": asset_uri,
            "@type": ["prov:Entity", "traceai:Asset"],
            "traceai:assetId": result.asset_id,
            "traceai:sha256": result.asset_hash,
            "traceai:sourceUri": source_uri,
            "traceai:sourceDomain": domain,
            "traceai:track": result.track.value if hasattr(result.track, "value") else str(result.track),
            "traceai:verdict": result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict),
            "traceai:score": result.score,
            "prov:wasGeneratedBy": {"@id": activity_uri},
        },
        # 2. Activity: Scan Processing
        {
            "@id": activity_uri,
            "@type": ["prov:Activity", "traceai:IngestionScan"],
            "prov:startedAtTime": result.scanned_at.isoformat(),
            "prov:endedAtTime": now_iso,
            "prov:wasAssociatedWith": {"@id": agent_uri},
            "prov:used": [{"@id": f"urn:traceai:source:{domain}"}],
        },
        # 3. Agent: TraceAI Ingestion Gateway
        {
            "@id": agent_uri,
            "@type": ["prov:Agent", "prov:SoftwareAgent"],
            "prov:label": f"TraceAI Ingestion Engine v{pipeline_version}",
        },
    ]

    if certificate_id:
        cert_entity = {
            "@id": f"urn:traceai:certificate:{certificate_id}",
            "@type": ["prov:Entity", "traceai:ClearanceCertificate"],
            "prov:wasDerivedFrom": {"@id": asset_uri},
            "prov:wasGeneratedBy": {"@id": activity_uri},
        }
        graph.append(cert_entity)

    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "traceai": "https://traceai.org/schema/prov#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@graph": graph,
    }


class LineageGraphStore:
    """Graph projection store supporting PROV-O traversals and domain-level queries."""

    def __init__(self):
        self._entities: dict[str, dict] = {}  # asset_hash -> entity
        self._activities: dict[str, dict] = {}
        self._agents: dict[str, dict] = {}
        self._edges: list[tuple[str, str, str]] = []  # (from_id, rel, to_id)

    def project_prov_o(self, prov_doc: dict[str, Any]) -> None:
        """Upsert PROV-O graph elements into memory / graph store."""
        for item in prov_doc.get("@graph", []):
            item_id = item["@id"]
            types = item.get("@type", [])

            if "prov:Entity" in types:
                self._entities[item_id] = item
                if "prov:wasGeneratedBy" in item:
                    self._edges.append((item_id, "wasGeneratedBy", item["prov:wasGeneratedBy"]["@id"]))
            elif "prov:Activity" in types:
                self._activities[item_id] = item
                if "prov:wasAssociatedWith" in item:
                    self._edges.append((item_id, "wasAssociatedWith", item["prov:wasAssociatedWith"]["@id"]))
            elif "prov:Agent" in types:
                self._agents[item_id] = item

    def get_assets_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """Query all assets derived from a given source domain."""
        matched = []
        for e in self._entities.values():
            if e.get("traceai:sourceDomain") == domain:
                matched.append(e)
        return matched

    def catch_up_from_audit_log(self, audit_records: list[dict[str, Any]]) -> int:
        """Asynchronously project missing audit log entries into graph store."""
        projected = 0
        for row in audit_records:
            asset_hash = row["asset_hash"]
            entity_uri = f"urn:traceai:asset:{asset_hash}"
            if entity_uri not in self._entities:
                # Build mock result
                parsed_payload = json.loads(row["raw_payload"])
                dummy_res = ScanResult.model_validate(parsed_payload)
                doc = build_prov_o_jsonld(
                    result=dummy_res,
                    source_uri=parsed_payload.get("source_uri", "https://example.com/asset"),
                    certificate_id=row.get("certificate_id"),
                )
                self.project_prov_o(doc)
                projected += 1
        return projected
