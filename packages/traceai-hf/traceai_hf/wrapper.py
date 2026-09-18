"""Hugging Face Dataset Ingestion Wrapper for TraceAI (Task Card T4.7)."""

from typing import Any, Callable, Optional


class TraceAIDatasetWrapper:
    """Wraps Hugging Face load_dataset to scan items in-flight before returning."""

    def __init__(self, scanner_func: Optional[Callable[[str], bool]] = None):
        self.scanner_func = scanner_func or (lambda text: True)

    def scan_item(self, item: dict[str, Any], text_key: str = "text") -> dict[str, Any]:
        """Inspect dataset sample and attach clearance verdict."""
        text = item.get(text_key, "")
        is_cleared = self.scanner_func(text)
        item["traceai_verdict"] = "PASSED" if is_cleared else "BLOCKED"
        return item
