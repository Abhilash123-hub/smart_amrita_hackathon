"""Generation-Time Leakage Detection (B5): ISACL-style probe intercepting memorized copyright disclosure."""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelClearanceRecord(BaseModel):
    """Post-training clearance record issued to an evaluated model."""
    model_id: str
    training_run_id: str
    probe_version: str = "ISACL-Probe-v0.1"
    leakage_incidents_detected: int
    emission_suppressed: bool
    status: str  # "CLEARED" or "LEAKAGE_DETECTED"
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GenerationLeakageProbe:
    """Inference-time gate protecting LLMs and RAG pipelines from emitting memorized copyrighted content."""

    def __init__(self, memorized_corpus: Optional[list[str]] = None, n_gram_window: int = 7):
        self.memorized_corpus = memorized_corpus or []
        self.n_gram_window = n_gram_window
        self.leakage_incidents = 0
        self._memorized_ngrams = self._build_ngram_index()

    def _build_ngram_index(self) -> set[tuple[str, ...]]:
        index = set()
        for doc in self.memorized_corpus:
            words = re.findall(r"\b\w+\b", doc.lower())
            for i in range(len(words) - self.n_gram_window + 1):
                index.add(tuple(words[i : i + self.n_gram_window]))
        return index

    def register_protected_text(self, text: str):
        self.memorized_corpus.append(text)
        self._memorized_ngrams = self._build_ngram_index()

    def inspect_and_gate_generation(
        self,
        generated_text: str,
        suppress: bool = True,
    ) -> tuple[bool, str, Optional[str]]:
        """Inspect model generated tokens before disclosure.
        
        Returns: (is_leakage, final_text, reason)
        Acceptance Criteria: Detects and can suppress emission of memorized passage at generation time.
        """
        words = re.findall(r"\b\w+\b", generated_text.lower())
        for i in range(len(words) - self.n_gram_window + 1):
            ngram = tuple(words[i : i + self.n_gram_window])
            if ngram in self._memorized_ngrams:
                self.leakage_incidents += 1
                snippet = " ".join(ngram)
                reason = f"ISACL Probe Triggered: Memorized sequence detected ('{snippet}')"
                logger.warning(reason)

                if suppress:
                    redacted = re.sub(
                        re.escape(snippet),
                        "[REDACTED: COPYRIGHT MEMORIZATION INTERCEPTED BY TRACEAI]",
                        generated_text,
                        flags=re.IGNORECASE,
                    )
                    return True, redacted, reason
                return True, generated_text, reason

        return False, generated_text, None

    def issue_model_record(self, model_id: str, training_run_id: str) -> ModelClearanceRecord:
        """Emit ModelClearanceRecord distinct from per-asset certificates (B5)."""
        return ModelClearanceRecord(
            model_id=model_id,
            training_run_id=training_run_id,
            leakage_incidents_detected=self.leakage_incidents,
            emission_suppressed=True,
            status="CLEARED" if self.leakage_incidents == 0 else "LEAKAGE_DETECTED",
        )
