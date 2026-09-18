"""Automated test suite for Part B: Capability Expansions (B1-B12)."""

from pathlib import Path
import pytest

from traceai.crypto.signer import CryptoSigner
from traceai.governance.blockchain import BlockchainLedger
from traceai.governance.confidence_router import ConfidenceBandRouter
from traceai.governance.connectors import CiCdGatekeeper, ManifestItem, TrainingManifest
from traceai.governance.dmca import DmcaIndexManager
from traceai.governance.leakage_probe import GenerationLeakageProbe
from traceai.governance.model_cards import generate_dataset_card
from traceai.governance.rules_engine import JurisdictionRulesEngine
from traceai.governance.sharing import CrossOrgIndexSharing
from traceai.schemas.asset import AssetInput, TrackType
from traceai.schemas.report import AssetStatus
from traceai.tracks.audio_track import AudioTrack, compute_acoustic_fingerprint
from traceai.tracks.base import MatchResult
from traceai.tracks.code_track import CodeTrack, normalize_ast_tokens
from traceai.tracks.video_track import VideoTrack


@pytest.mark.asyncio
async def test_audio_track(tmp_path: Path):
    """B1: Acceptance criteria: detects duplicate audio via acoustic fingerprint."""
    index_dir = tmp_path / "audio_index"
    index_dir.mkdir()
    audio_sample = b"RIFF" + b"\x00" * 4 + b"WAVE" + b"fmt " + b"\x10\x00\x00\x00" + b"\x01\x00" * 4 + b"data" + b"AUDIOPEAKDATA" * 50
    ref_file = index_dir / "protected_song.wav"
    ref_file.write_bytes(audio_sample)

    query_file = tmp_path / "query.wav"
    query_file.write_bytes(audio_sample)
    asset = AssetInput.from_file(query_file)
    assert asset.track == TrackType.AUDIO

    track = AudioTrack()
    match = await track.evaluate(asset, index_dir=index_dir)
    assert match.is_match is True
    assert "protected_song" in match.matched_source
    assert match.similarity_score >= 0.88


@pytest.mark.asyncio
async def test_code_track_ast_and_gpl(tmp_path: Path):
    """B3: Acceptance criteria: detects renamed-variables copy of known GPL function."""
    index_dir = tmp_path / "code_index"
    index_dir.mkdir()

    # Original GPL function
    gpl_code = """
# GNU General Public License v3.0
def calculate_secure_digest(payload_data):
    accumulator = 0
    for byte_val in payload_data:
        accumulator = (accumulator * 31 + byte_val) % 1000000007
    return accumulator
"""
    (index_dir / "crypto_lib.py").write_text(gpl_code, encoding="utf-8")

    # Ingested code: variables and function renamed, but identical AST structure
    renamed_copy = """
def compute_hash(input_buffer):
    result = 0
    for item in input_buffer:
        result = (result * 31 + item) % 1000000007
    return result
"""
    query_file = tmp_path / "app_module.py"
    query_file.write_text(renamed_copy, encoding="utf-8")
    asset = AssetInput.from_file(query_file)
    assert asset.track == TrackType.CODE

    track = CodeTrack()
    match = await track.evaluate(asset, index_dir=index_dir)
    assert match.is_match is True
    assert "GPL" in match.matched_source
    assert match.similarity_score >= 0.85


def test_confidence_band_routing_and_human_review(tmp_path: Path):
    """B4: Acceptance criteria: mid-band routes to HUMAN_REVIEW; decisions logged to PROV-O."""
    router = ConfidenceBandRouter(db_path=tmp_path / "review.db")
    signer = CryptoSigner.generate()

    f = tmp_path / "asset.txt"
    f.write_text("Excerpt", encoding="utf-8")
    asset = AssetInput.from_file(f)

    # Mid-confidence match (e.g. 0.76 is between 0.70 and 0.85)
    match = MatchResult(
        is_match=False,
        similarity_score=0.76,
        matched_source="© Similar Work",
    )
    band, status = router.route_asset(asset, match)
    assert band == "HUMAN_REVIEW"
    assert status == AssetStatus.HUMAN_REVIEW

    # Reviewer adjudicates
    queue = router.get_pending_review_queue()
    assert len(queue) == 1

    res = router.resolve_review(
        asset_id=asset.asset_id,
        reviewer_id="legal_counsel_42",
        approve=True,
        signer=signer,
    )
    assert res["resolution"] == "APPROVED"
    assert res["prov_attribution"] == "urn:traceai:reviewer:legal_counsel_42"
    assert res["certificate"] is not None


def test_jurisdiction_rules_engine():
    """B12: Acceptance criteria: same asset & confidence produces different outcomes under EU vs US rules."""
    engine = JurisdictionRulesEngine()

    # Asset with 0.82 confidence and TDM reservation asserted
    # Under EU rules: strict TDM opt-out -> BLOCKED
    outcome_eu, rule_eu = engine.evaluate_jurisdiction(
        jurisdiction="EU",
        confidence_score=0.82,
        tdm_opted_out=True,
        default_outcome="HUMAN_REVIEW",
    )
    assert outcome_eu == "BLOCKED"
    assert rule_eu == "EU_TDM_RESERVATION_BLOCK"

    # Under US rules: no opt-out / fair-use mid-band consideration -> HUMAN_REVIEW
    outcome_us, rule_us = engine.evaluate_jurisdiction(
        jurisdiction="US",
        confidence_score=0.82,
        tdm_opted_out=False,
        default_outcome="CLEAR",
    )
    assert outcome_us == "HUMAN_REVIEW"
    assert rule_us == "US_FAIR_USE_MID_BAND"


def test_dmca_delta_reevaluation(tmp_path: Path):
    """B6: Acceptance criteria: asset cleared under v1 is flagged under v2 via delta re-evaluation only."""
    dmca = DmcaIndexManager(db_path=tmp_path / "dmca.db")

    f = tmp_path / "user_article.txt"
    f.write_text("Exclusive chapter from an upcoming scientific release.", encoding="utf-8")
    asset = AssetInput.from_file(f)

    # Register as cleared under v1
    dmca.register_cleared_asset(asset, status="PASSED")
    assert dmca.get_current_index_version() == 1

    # Rightsholder submits takedown notice for that text -> index increments to v2
    dmca.submit_takedown(
        notice_id="notice_001",
        rightsholder="Springer Nature",
        work_title="Scientific Release 2026",
        track="TEXT",
        sample_content="Exclusive chapter from an upcoming scientific release.",
    )
    assert dmca.get_current_index_version() == 2

    # Delta scan checks ONLY delta items from v1 to v2
    flagged = dmca.reevaluate_delta(from_version=1, to_version=2)
    assert len(flagged) == 1
    assert flagged[0]["asset_id"] == asset.asset_id
    assert flagged[0]["action_required"] == "REVOKE_AND_BLOCK"


def test_cross_org_zero_knowledge_sharing():
    """B7: Acceptance criteria: two orgs detect infringement match via shared LSH hashes without raw text."""
    org_a = CrossOrgIndexSharing(org_id="Org-Alpha")
    org_b = CrossOrgIndexSharing(org_id="Org-Beta")

    secret_text = "Highly classified proprietary source materials distributed across academic consortium."
    # Org A exports signal
    signal_a = org_a.export_infringement_signal("doc_001", "Confidential Report", secret_text)
    assert "lsh_fingerprints" in signal_a
    assert secret_text not in str(signal_a)  # Raw text never shared!

    # Org B imports signal
    org_b.import_shared_signals(signal_a)

    # Org B queries matching text
    match = org_b.query_cross_org(secret_text)
    assert match is not None
    assert match["matched_org"] == "Org-Alpha"
    assert match["zero_knowledge_proof"] is True


def test_blockchain_ledger():
    """B8: Acceptance criteria: certificate verified against on-chain block hash."""
    ledger = BlockchainLedger()
    cert_id = "cert_abc_123"
    asset_hash = "sha256:7777777777777777777777777777777777777777777777777777777777777777"
    sig = "SGVsbG9Xb3JsZFNpZ25hdHVyZQ=="

    tx_id = ledger.anchor_certificate(cert_id, asset_hash, sig)
    assert tx_id.startswith("tx:")

    verification = ledger.verify_on_chain(cert_id, asset_hash)
    assert verification["verified"] is True
    assert verification["immutable"] is True


def test_cicd_gatekeeper():
    """B9: Acceptance criteria: CI gate fails and reports specific offending non-cleared assets."""
    gatekeeper = CiCdGatekeeper()
    hash_clean = "sha256:aaaa"
    hash_blocked = "sha256:bbbb"

    gatekeeper.register_cleared_hash(hash_clean, "PASSED")
    gatekeeper.register_cleared_hash(hash_blocked, "BLOCKED")

    # Manifest with 1 clean and 1 blocked asset
    manifest = TrainingManifest(
        training_run_id="run_999",
        model_name="GPT-Trace",
        manifest_assets=[
            ManifestItem(asset_id="file1.txt", asset_hash=hash_clean),
            ManifestItem(asset_id="file2.txt", asset_hash=hash_blocked),
        ],
    )

    result = gatekeeper.evaluate_manifest(manifest)
    assert result.status == "FAIL"
    assert result.unresolved_count == 1
    assert result.offending_assets[0]["asset_id"] == "file2.txt"


def test_hf_dataset_card_generator():
    """B11: Acceptance criteria: generates valid Hugging Face YAML dataset card from PROV-O graphs."""
    prov_graphs = [
        {
            "prov:wasGeneratedBy": {
                "traceai:resolutionStatus": "PASSED",
                "traceai:certificateId": "cert_uuid_001",
                "traceai:prefilter_decision": {"license_hint": "Apache-2.0"},
            },
            "prov:wasDerivedFrom": {"prov:atLocation": "https://example.com/dataset.txt"},
        }
    ]
    card = generate_dataset_card("My-Clean-Dataset", "run_123", prov_graphs)
    assert "dataset_name: My-Clean-Dataset" in card
    assert "license: other" in card
    assert "cert_uuid_001" in card


def test_isacl_generation_leakage_probe():
    """B5: Acceptance criteria: detects and suppresses emission of memorized passage at generation time."""
    probe = GenerationLeakageProbe(n_gram_window=5)
    memorized_passage = "call me ishmael some years ago never mind how long precisely"
    probe.register_protected_text(memorized_passage)

    generated_output = "As the story famously begins, Call me Ishmael some years ago never mind how long precisely, he said."
    is_leakage, final_text, reason = probe.inspect_and_gate_generation(generated_output, suppress=True)

    assert is_leakage is True
    assert "[REDACTED: COPYRIGHT MEMORIZATION INTERCEPTED BY TRACEAI]" in final_text
    record = probe.issue_model_record("model_llama_01", "run_881")
    assert record.leakage_incidents_detected == 1
