"""Verification Tests for W3C PROV-O Lineage Projections (Task Card T2.4)."""

import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest

from src.traceai.core.models import ScanResult, Track, Verdict
from src.traceai.lineage.prov_o import LineageGraphStore, build_prov_o_jsonld


def test_entity_activity_agent_triangle():
    """Verify generated JSON-LD contains the full Entity-Activity-Agent triangle."""
    now = datetime.now(timezone.utc)
    dummy_hash = "sha256:" + "f" * 64

    res = ScanResult(
        asset_id="asset-lineage-01",
        track=Track.TEXT,
        verdict=Verdict.PASSED,
        score=0.10,
        matched_source=None,
        asset_hash=dummy_hash,
        scanned_at=now,
    )

    cert_id = str(uuid4())
    doc = build_prov_o_jsonld(
        result=res,
        source_uri="https://commoncrawl.org/dataset/2026/sample.txt",
        certificate_id=cert_id,
    )

    graph_nodes = doc.get("@graph", [])
    types = [t for node in graph_nodes for t in node.get("@type", [])]

    assert "prov:Entity" in types
    assert "prov:Activity" in types
    assert "prov:Agent" in types

    store = LineageGraphStore()
    store.project_prov_o(doc)
    assert len(store._entities) >= 1
    assert len(store._activities) >= 1
    assert len(store._agents) >= 1


def test_domain_level_query():
    """Verify domain-level queries return assets derived from given source domain."""
    store = LineageGraphStore()
    now = datetime.now(timezone.utc)

    # Asset 1 from wikipedia.org
    res1 = ScanResult(
        asset_id="wiki-art-1",
        track=Track.TEXT,
        verdict=Verdict.PASSED,
        score=0.05,
        asset_hash="sha256:" + "1" * 64,
        scanned_at=now,
    )
    doc1 = build_prov_o_jsonld(res1, source_uri="https://en.wikipedia.org/wiki/Artificial_intelligence")
    store.project_prov_o(doc1)

    # Asset 2 from nytimes.com
    res2 = ScanResult(
        asset_id="nyt-art-2",
        track=Track.TEXT,
        verdict=Verdict.BLOCKED,
        score=0.92,
        asset_hash="sha256:" + "2" * 64,
        scanned_at=now,
    )
    doc2 = build_prov_o_jsonld(res2, source_uri="https://www.nytimes.com/technology/article.html")
    store.project_prov_o(doc2)

    # Query domain
    wiki_assets = store.get_assets_by_domain("en.wikipedia.org")
    assert len(wiki_assets) == 1
    assert wiki_assets[0]["traceai:assetId"] == "wiki-art-1"

    nyt_assets = store.get_assets_by_domain("www.nytimes.com")
    assert len(nyt_assets) == 1
    assert nyt_assets[0]["traceai:assetId"] == "nyt-art-2"


def test_catch_up_from_audit_log():
    """Verify async catch-up synchronization projects unrecorded assets from audit log."""
    store = LineageGraphStore()
    dummy_hash = "sha256:" + "9" * 64

    audit_records = [
        {
            "asset_hash": dummy_hash,
            "raw_payload": json.dumps({
                "asset_id": "audit-asset-99",
                "track": "TEXT",
                "verdict": "PASSED",
                "score": 0.02,
                "asset_hash": dummy_hash,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "source_uri": "https://huggingface.co/datasets/sample",
            }),
            "certificate_id": str(uuid4()),
        }
    ]

    count = store.catch_up_from_audit_log(audit_records)
    assert count == 1
    assets = store.get_assets_by_domain("huggingface.co")
    assert len(assets) == 1
    assert assets[0]["traceai:assetId"] == "audit-asset-99"
