"""Verification Tests for Observability Stack & Telemetry (Task Card T4.5)."""

from src.traceai.telemetry import TelemetryCollector


def test_telemetry_metrics_and_spans():
    """Verify latency histogram recording, p95 computation, and end-to-end trace spans."""
    collector = TelemetryCollector()

    collector.record_verdict("PASSED", 120.0)
    collector.record_verdict("PASSED", 150.0)
    collector.record_verdict("BLOCKED", 410.0)

    assert collector.verdict_counts["PASSED"] == 2
    assert collector.verdict_counts["BLOCKED"] == 1
    assert collector.get_p95_latency() <= 450.0

    # Trace span across planes
    span = collector.start_span("gateway_ingress", plane="ingestion", attributes={"asset_id": "a-1"})
    assert span["plane"] == "ingestion"
    assert len(collector.spans) == 1
