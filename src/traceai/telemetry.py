"""OpenTelemetry Tracing and Prometheus Metrics for TraceAI (Task Card T4.5)."""

import time
from typing import Any, Dict


class TelemetryCollector:
    """Collects scan latency histograms, queue depth, and verdict counters."""

    def __init__(self):
        self.verdict_counts: Dict[str, int] = {"PASSED": 0, "BLOCKED": 0, "REVIEW": 0}
        self.scan_latencies: list[float] = []
        self.queue_depth: int = 0
        self.spans: list[dict] = []

    def record_verdict(self, verdict: str, latency_ms: float):
        self.verdict_counts[verdict] = self.verdict_counts.get(verdict, 0) + 1
        self.scan_latencies.append(latency_ms)

    def start_span(self, name: str, plane: str, attributes: dict[str, Any]) -> dict:
        span = {
            "name": name,
            "plane": plane,
            "attributes": attributes,
            "start_time": time.time(),
        }
        self.spans.append(span)
        return span

    def get_p95_latency(self) -> float:
        import numpy as np
        if not self.scan_latencies:
            return 0.0
        return float(np.percentile(self.scan_latencies, 95))
