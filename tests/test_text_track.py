"""Verification Tests for Text Track Pipeline & Early Exit Gate (Task Card T1.3)."""

from pathlib import Path
import pytest
from src.traceai.config import GatewayConfig
from src.traceai.core.models import Verdict
from src.traceai.pipelines.text_track import TextTrackPipeline


@pytest.fixture
def text_corpus():
    """Load reference copyright corpus from mock_data/copyright_index/texts."""
    ref_dir = Path("mock_data/copyright_index/texts")
    corpus = []
    for p in sorted(list(ref_dir.glob("*.txt"))):
        corpus.append((p.name, p.read_text(encoding="utf-8")))
    return corpus


def test_early_exit_skips_cross_encoder_on_unrelated_text(text_corpus):
    """Verify early-exit gate skips cross-encoder scoring when recall similarity < 0.5."""
    pipeline = TextTrackPipeline()
    spy = {}

    unrelated_text = (
        "Quantum computing relies on quantum bits, or qubits, which can exist in multiple states simultaneously. "
        "Superposition and entanglement are fundamental principles that allow quantum computers to solve "
        "certain computational problems significantly faster than classical systems."
    )

    verdict, score, matched_src, telemetry = pipeline.evaluate_text(
        unrelated_text,
        candidate_corpus=text_corpus,
        asset_id="asset-unrelated",
        spy_recorder=spy,
    )

    assert verdict == Verdict.PASSED
    assert score == 0.0
    assert spy["early_exit_triggered"] is True
    assert spy["cross_encoder_called"] is False
    assert telemetry["gate"] == "early_exit"


def test_flagging_dirty_paraphrased_assets(text_corpus):
    """Verify dirty text assets with 30% synonym replacement are flagged."""
    dirty_dir = Path("mock_data/dirty_dataset")
    pipeline = TextTrackPipeline()

    dirty_files = sorted(list(dirty_dir.glob("dirty_text_*.public_domain")))
    assert len(dirty_files) >= 5, "At least 5 dirty text files expected"

    flagged_count = 0
    for f in dirty_files[:10]:
        content = f.read_text(encoding="utf-8")
        spy = {}
        verdict, score, matched_src, telemetry = pipeline.evaluate_text(
            content,
            candidate_corpus=text_corpus,
            asset_id=f.name,
            spy_recorder=spy,
        )
        assert spy["cross_encoder_called"] is True
        # Either BLOCKED (>= 0.85) or high similarity candidate flagged
        if verdict in (Verdict.BLOCKED, Verdict.REVIEW) or score >= 0.70:
            flagged_count += 1

    assert flagged_count == min(10, len(dirty_files))


def test_clean_holdout_passes_under_threshold(text_corpus):
    """Verify clean holdout texts pass with scores below 0.60."""
    pipeline = TextTrackPipeline()

    clean_samples = [
        "A recipe for chocolate chip cookies requires flour, butter, brown sugar, eggs, and vanilla extract.",
        "The Python programming language was created by Guido van Rossum and first released in 1991.",
        "Photosynthesis is the process used by plants and other organisms to convert light energy into chemical energy.",
    ]

    for idx, sample in enumerate(clean_samples):
        verdict, score, _, telemetry = pipeline.evaluate_text(
            sample,
            candidate_corpus=text_corpus,
            asset_id=f"clean-{idx}",
        )
        assert verdict == Verdict.PASSED
        assert score < 0.60
