"""Dirty Dataset Generator & Adversarial Fixture Verifier (Task Card T0.5)."""

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps

SYNONYMS = {
    "truth": "reality",
    "acknowledged": "recognized",
    "possession": "ownership",
    "fortune": "wealth",
    "want": "need",
    "wife": "spouse",
    "feeling": "emotion",
    "views": "perspectives",
    "entering": "stepping into",
    "neighbourhood": "community",
    "fixed": "settled",
    "rightful": "legitimate",
    "property": "belonging",
    "morning": "dawn",
    "dreams": "slumber",
    "transformed": "metamorphosed",
    "bed": "mattress",
    "horrible": "dreadful",
    "vermin": "creature",
    "armor-like": "shield-like",
    "back": "spine",
    "lifted": "raised",
    "brown": "dusky",
    "belly": "abdomen",
    "divided": "sectioned",
    "arches": "curves",
    "quilt": "blanket",
    "sliding": "slipping",
    "helplessly": "powerlessly",
    "numerous": "countless",
    "pitifully": "pathetically",
    "glance": "gaze",
    "window": "casement",
    "weather": "climate",
    "drops": "droplets",
}


def paraphrase_text(text: str, swap_prob: float = 0.30, seed: int = 42) -> str:
    """Apply ~30% synonym replacement to generate an evasive paraphrased text."""
    rng = random.Random(seed)
    words = text.split()
    paraphrased = []
    for word in words:
        clean = word.strip(".,;:\"'!?()").lower()
        if clean in SYNONYMS and rng.random() < swap_prob:
            sub = SYNONYMS[clean]
            # preserve capitalization
            if word[0].isupper():
                sub = sub.capitalize()
            if word[-1] in ".,;:\"'!?()":
                sub += word[-1]
            paraphrased.append(sub)
        else:
            paraphrased.append(word)
    return " ".join(paraphrased)


def perturb_image(img: Image.Image, seed: int = 42) -> Image.Image:
    """Apply 95-98% crop, LANCZOS resize, and JPEG recompression to evade exact hashing."""
    import io
    rng = random.Random(seed)
    w, h = img.size
    crop_factor = rng.uniform(0.96, 0.98)
    new_w, new_h = int(w * crop_factor), int(h * crop_factor)
    left = (w - new_w) // 2
    top = (h - new_h) // 2

    cropped = img.crop((left, top, left + new_w, top + new_h))
    resized = cropped.resize((w, h), resample=Image.Resampling.LANCZOS)
    
    # JPEG recompression to modify low-level bitstream
    buf = io.BytesIO()
    resized.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    recompressed = Image.open(buf)
    return ImageOps.autocontrast(recompressed)


def generate_dataset(output_dir: Path, ref_index_dir: Path, seed: int = 42) -> dict:
    """Generate 10 dirty text and 10 dirty image assets with source attribution manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"generated_at_seed": seed, "assets": []}

    # Generate text assets
    text_ref_dir = ref_index_dir / "texts"
    ref_texts = sorted(list(text_ref_dir.glob("*.txt")))[:10]
    for idx, ref_file in enumerate(ref_texts, start=1):
        content = ref_file.read_text(encoding="utf-8")
        dirty_content = paraphrase_text(content, seed=seed + idx)
        out_name = f"dirty_text_{idx:02d}.public_domain"
        out_file = output_dir / out_name
        out_file.write_text(dirty_content, encoding="utf-8")

        ref_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        dirty_hash = hashlib.sha256(dirty_content.encode("utf-8")).hexdigest()

        manifest["assets"].append({
            "asset_id": out_name,
            "track": "TEXT",
            "source_reference_file": ref_file.name,
            "reference_sha256": f"sha256:{ref_hash}",
            "dirty_sha256": f"sha256:{dirty_hash}",
            "exact_hash_match": ref_hash == dirty_hash,
        })

    # Generate image assets
    img_ref_dir = ref_index_dir / "images"
    ref_imgs = sorted(list(img_ref_dir.glob("*.png")))[:10]
    for idx, ref_file in enumerate(ref_imgs, start=1):
        with Image.open(ref_file) as img:
            dirty_img = perturb_image(img, seed=seed + idx)
            out_name = f"dirty_image_{idx:02d}.public_domain"
            out_file = output_dir / out_name
            dirty_img.save(out_file, format="PNG")

            with open(ref_file, "rb") as f:
                ref_hash = hashlib.sha256(f.read()).hexdigest()
            with open(out_file, "rb") as f:
                dirty_hash = hashlib.sha256(f.read()).hexdigest()

            manifest["assets"].append({
                "asset_id": out_name,
                "track": "IMAGE",
                "source_reference_file": ref_file.name,
                "reference_sha256": f"sha256:{ref_hash}",
                "dirty_sha256": f"sha256:{dirty_hash}",
                "exact_hash_match": ref_hash == dirty_hash,
            })

    manifest_file = output_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def check_dirty_dataset(data_dir: Path, ref_dir: Path) -> bool:
    """Verify that 10 dirty text and 10 dirty image assets exist and naive exact hash matches 0%."""
    manifest_path = data_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"[FAIL] Manifest not found at {manifest_path}", file=sys.stderr)
        return False

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest.get("assets", [])

    text_assets = [a for a in assets if a.get("track") == "TEXT"]
    image_assets = [a for a in assets if a.get("track") == "IMAGE"]

    if len(text_assets) < 10 or len(image_assets) < 10:
        print(f"[FAIL] Incomplete assets: {len(text_assets)} text, {len(image_assets)} image.", file=sys.stderr)
        return False

    # Check that naive exact-hash matching catches ZERO dirty assets (proving evasion)
    exact_matches = [a for a in assets if a.get("exact_hash_match") is True]
    if len(exact_matches) > 0:
        print(f"[FAIL] Naive exact hash matched {len(exact_matches)} assets! Evasion failed.", file=sys.stderr)
        return False

    print(f"[PASS] Verified dirty dataset: {len(text_assets)} text + {len(image_assets)} images.")
    print(f"[PASS] Naive exact-hash matching caught 0 assets (100% evasion achieved).")
    return True


def main():
    parser = argparse.ArgumentParser(description="TraceAI Dirty Dataset Generator (T0.5)")
    parser.add_argument("--check", action="store_true", help="Verify existing dirty dataset fixture")
    parser.add_argument("--output-dir", default="./mock_data/dirty_dataset", help="Output directory")
    parser.add_argument("--ref-dir", default="./mock_data/copyright_index", help="Reference index directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    ref_dir = Path(args.ref_dir)

    if args.check:
        success = check_dirty_dataset(out_dir, ref_dir)
        sys.exit(0 if success else 1)

    print(f"Generating dirty dataset in {out_dir} from {ref_dir} (seed={args.seed})...")
    manifest = generate_dataset(out_dir, ref_dir, seed=args.seed)
    print(f"Done. Generated {len(manifest['assets'])} dirty assets with manifest.json.")


if __name__ == "__main__":
    main()
