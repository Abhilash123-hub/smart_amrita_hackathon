"""Verification Tests for Image Track Pipeline & Successive Filtering (Task Cards T1.4, T1.5)."""

import io
from pathlib import Path
import pytest
from PIL import Image, ImageEnhance
import imagehash

from src.traceai.config import GatewayConfig
from src.traceai.core.models import Verdict
from src.traceai.db.redis_cache import PHashRedisCache
from src.traceai.pipelines.image_track import ImageTrackPipeline


@pytest.fixture
def image_env():
    """Setup cached reference index dictionary and pipeline."""
    ref_dir = Path("mock_data/copyright_index/images")
    cache = PHashRedisCache()

    # Pre-populate cache dictionary
    phash_dict = {}
    for p in sorted(list(ref_dir.glob("*.png")) + list(ref_dir.glob("*.jpg"))):
        with Image.open(p) as img:
            phash_dict[p.name] = str(imagehash.phash(img))

    cache.load_dictionary(phash_dict)
    config = GatewayConfig(image_phash_hamming_threshold=8)
    pipeline = ImageTrackPipeline(config=config, cache=cache)
    return pipeline, ref_dir, cache


def test_phash_dictionary_round_trip(image_env):
    """Verify dictionary round-trips through Redis / cache without loss."""
    _, _, cache = image_env
    data = cache.get_all()
    assert len(data) >= 10
    sample_key = next(iter(data.keys()))
    assert len(data[sample_key]) == 16  # 64-bit hex hash


def test_phash_recalls_color_shifted_and_recompressed_copies(image_env):
    """Verify lightly color-shifted or recompressed copies of seed images are recalled."""
    pipeline, ref_dir, _ = image_env
    ref_img_path = next(iter(ref_dir.glob("*.png")))

    with Image.open(ref_img_path) as img:
        # Realistic JPEG recompression at quality 92 + slight color enhancement
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92)
        buf.seek(0)
        recompressed = ImageEnhance.Color(Image.open(buf)).enhance(1.02)

        q_hash = pipeline.compute_phash(recompressed)
        matches = pipeline.cache.query_hamming(q_hash, max_distance=5)

        assert len(matches) > 0
        matched_names = [m[0] for m in matches]
        assert ref_img_path.name in matched_names


def test_unrelated_images_pass_with_zero_gpu_invocations(image_env):
    """Verify unrelated image exits at Stage 1 coarse filter with zero GPU invocations."""
    pipeline, ref_dir, _ = image_env
    spy = {}

    # Distinct geometric noise image with completely different pHash
    unrelated_img = Image.new("RGB", (300, 300), color=(128, 64, 32))

    verdict, score, matched_name, telemetry = pipeline.evaluate_image(
        unrelated_img,
        ref_images_dir=ref_dir,
        asset_id="asset-unrelated-image",
        spy_recorder=spy,
    )

    assert verdict == Verdict.PASSED
    assert score == 0.0
    assert spy["stage1_filtered"] is True
    assert spy["clip_called"] is False
    assert telemetry["gpu_invoked"] is False


def test_dirty_cropped_images_blocked(image_env):
    """Verify dirty images (95-98% crops) are recalled and blocked."""
    pipeline, ref_dir, _ = image_env
    dirty_dir = Path("mock_data/dirty_dataset")
    dirty_files = sorted(list(dirty_dir.glob("dirty_image_*.public_domain")))
    assert len(dirty_files) >= 5

    flagged_count = 0
    for f in dirty_files[:5]:
        with Image.open(f) as img:
            spy = {}
            verdict, score, matched_name, telemetry = pipeline.evaluate_image(
                img,
                ref_images_dir=ref_dir,
                asset_id=f.name,
                spy_recorder=spy,
            )
            assert spy["clip_called"] is True
            if verdict in (Verdict.BLOCKED, Verdict.REVIEW) or score >= 0.70:
                flagged_count += 1

    assert flagged_count >= 4
