"""Evidence Locker Artifact Generator: Visual Proof Crops with OpenCV (Task Card T1.6)."""

from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def locate_best_match_bbox(
    query_img: Image.Image,
    source_img: Image.Image,
) -> Tuple[int, int, int, int]:
    """Locate bounding box (x, y, w, h) of query inside source via OpenCV template match."""
    q_rgb = np.array(query_img.convert("RGB"))
    s_rgb = np.array(source_img.convert("RGB"))

    if HAS_CV2:
        q_gray = cv2.cvtColor(q_rgb, cv2.COLOR_RGB2GRAY)
        s_gray = cv2.cvtColor(s_rgb, cv2.COLOR_RGB2GRAY)

        # Handle size scaling if query is larger than source
        if q_gray.shape[0] > s_gray.shape[0] or q_gray.shape[1] > s_gray.shape[1]:
            # Invert template roles
            res = cv2.matchTemplate(q_gray, s_gray, cv2.TM_CCOEFF_NORMED)
            _, _, _, max_loc = cv2.minMaxLoc(res)
            return max_loc[0], max_loc[1], s_gray.shape[1], s_gray.shape[0]

        res = cv2.matchTemplate(s_gray, q_gray, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        return max_loc[0], max_loc[1], q_gray.shape[1], q_gray.shape[0]
    else:
        # Fallback bounding box
        sw, sh = source_img.size
        return int(sw * 0.1), int(sh * 0.1), int(sw * 0.8), int(sh * 0.8)


def render_evidence_composite(
    query_img: Image.Image,
    source_img: Image.Image,
    score: float,
    asset_hash: str,
    matched_source_name: str,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """Render side-by-side evidence PNG with bounding box and burned-in margin metrics.
    
    Deterministic: No timestamps are drawn on pixels to ensure reproducible hashes.
    """
    # Normalize sizes to uniform display height (400px)
    target_h = 400
    q_scale = target_h / max(query_img.height, 1)
    q_w = max(int(query_img.width * q_scale), 1)
    q_resized = query_img.convert("RGB").resize((q_w, target_h), Image.Resampling.LANCZOS)

    s_scale = target_h / max(source_img.height, 1)
    s_w = max(int(source_img.width * s_scale), 1)
    s_resized = source_img.convert("RGB").resize((s_w, target_h), Image.Resampling.LANCZOS)

    # Locate bounding box on source
    bx, by, bw, bh = locate_best_match_bbox(query_img, source_img)
    # Scale bbox to resized source coordinates
    scaled_bx = int(bx * s_scale)
    scaled_by = int(by * s_scale)
    scaled_bw = int(bw * s_scale)
    scaled_bh = int(bh * s_scale)

    # Draw neon-red bounding box on source copy
    s_boxed = s_resized.copy()
    draw_box = ImageDraw.Draw(s_boxed)
    draw_box.rectangle(
        [scaled_bx, scaled_by, scaled_bx + scaled_bw, scaled_by + scaled_bh],
        outline="#EF4444",
        width=3,
    )

    # Canvas setup with dark security-ops margin
    header_h = 60
    canvas_w = q_w + s_w + 30
    canvas_h = target_h + header_h + 30
    canvas = Image.new("RGB", (canvas_w, canvas_h), color="#0B1220")  # bg/root

    # Paste images
    canvas.paste(q_resized, (10, header_h + 10))
    canvas.paste(s_boxed, (q_w + 20, header_h + 10))

    # Burn metrics into margin
    draw = ImageDraw.Draw(canvas)
    header_text_1 = f"TRACEAI EVIDENCE VAULT | VERDICT: BLOCKED | SIMILARITY: {score:.4f}"
    header_text_2 = f"ASSET: {asset_hash[:24]}... | MATCHED: {matched_source_name}"

    draw.text((12, 12), header_text_1, fill="#F87171")       # status/blocked
    draw.text((12, 34), header_text_2, fill="#9FB2C8")       # text/muted
    draw.text((12, header_h + 14), "INGESTED (CROPPED)", fill="#38BDF8")
    draw.text((q_w + 22, header_h + 14), "MATCHED SOURCE (CORRELATION BBOX)", fill="#EF4444")

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, format="PNG")

    return canvas
