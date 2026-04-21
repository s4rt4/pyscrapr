"""Visual diff service for two screenshots.

Uses Pillow (already a dependency) to compute pixel-level differences and
produce either a side-by-side composite (A | B | diff overlay on B) or an
overlay-only image (B with red semi-transparent mask on changed pixels).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFont

logger = logging.getLogger("pyscrapr.screenshot")


def _load_rgba(path: Path) -> Image.Image:
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def _resize_to_match(a: Image.Image, b: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Pad/resize both images to the larger bounding box, preserving A's aspect.

    We use padding rather than stretching so visual comparison stays honest:
    the smaller image sits in the top-left corner of a transparent canvas the
    size of the larger one.
    """
    w = max(a.width, b.width)
    h = max(a.height, b.height)
    if a.size != (w, h):
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(a, (0, 0))
        a = canvas
    if b.size != (w, h):
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(b, (0, 0))
        b = canvas
    return a, b


def _build_diff_mask(a: Image.Image, b: Image.Image, threshold: int) -> tuple[Image.Image, dict[str, Any]]:
    """Return (mask_L, stats). Mask is L mode where 255 = differs."""
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    # Max channel delta per pixel
    bands = diff.split()
    # Combine via lighter to get per-pixel max
    max_band = bands[0]
    for band in bands[1:]:
        max_band = ImageChops.lighter(max_band, band)
    # Threshold to mask
    mask = max_band.point(lambda v: 255 if v > threshold else 0, mode="L")
    bbox = mask.getbbox()

    # Count different pixels
    # Using histogram avoids allocating a list of every pixel
    hist = mask.histogram()
    different_pixels = int(hist[255]) if len(hist) >= 256 else 0
    total_pixels = a.width * a.height
    stats = {
        "width": a.width,
        "height": a.height,
        "total_pixels": total_pixels,
        "different_pixels": different_pixels,
        "diff_ratio": (different_pixels / total_pixels) if total_pixels else 0.0,
        "bbox": list(bbox) if bbox else None,
    }
    return mask, stats


def _overlay_on(base: Image.Image, mask: Image.Image) -> Image.Image:
    """Composite a red semi-transparent layer on base where mask != 0."""
    red = Image.new("RGBA", base.size, (255, 0, 0, 120))
    out = base.convert("RGBA").copy()
    out.paste(red, (0, 0), mask=mask)
    return out


def _label(img: Image.Image, text: str) -> Image.Image:
    """Draw a small label strip at the top-left corner of img."""
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    pad = 4
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = 80, 12
    draw.rectangle([0, 0, tw + pad * 2, th + pad * 2], fill=(0, 0, 0, 180))
    draw.text((pad, pad), text, fill=(255, 255, 255, 255), font=font)
    return img


async def compare(
    job_id_a: str,
    filename_a: str,
    job_id_b: str,
    filename_b: str,
    output_dir: Path,
    mode: str = "side_by_side",
    threshold: int = 10,
    source_dir: Path | None = None,
) -> dict[str, Any]:
    """Compare two screenshot files and produce a diff composite image.

    ``source_dir`` is where the input files live (defaults to ``output_dir``'s
    parent screenshots folder when None).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    src = source_dir or output_dir.parent
    path_a = src / filename_a
    path_b = src / filename_b
    if not path_a.exists():
        raise FileNotFoundError(f"File A tidak ditemukan: {filename_a}")
    if not path_b.exists():
        raise FileNotFoundError(f"File B tidak ditemukan: {filename_b}")

    img_a = _load_rgba(path_a)
    img_b = _load_rgba(path_b)
    img_a, img_b = _resize_to_match(img_a, img_b)

    mask, stats = _build_diff_mask(img_a, img_b, threshold)

    comparison_id = str(uuid.uuid4())

    if mode == "overlay":
        composite = _overlay_on(img_b, mask)
    else:
        # Side-by-side: A | B | B+overlay
        overlay = _overlay_on(img_b, mask)
        w, h = img_a.size
        composite = Image.new("RGBA", (w * 3 + 8, h), (20, 20, 20, 255))
        composite.paste(img_a, (0, 0))
        composite.paste(img_b, (w + 4, 0))
        composite.paste(overlay, (w * 2 + 8, 0))
        _label(composite, "A")
        # Labels on B / Diff panels via cropped subregions
        sub_b = composite.crop((w + 4, 0, w * 2 + 4, h))
        _label(sub_b, "B")
        composite.paste(sub_b, (w + 4, 0))
        sub_d = composite.crop((w * 2 + 8, 0, w * 3 + 8, h))
        _label(sub_d, "Diff")
        composite.paste(sub_d, (w * 2 + 8, 0))

    out_path = output_dir / f"{comparison_id}.png"
    composite.convert("RGB").save(out_path, format="PNG", optimize=True)

    logger.info(
        "Compare done: %s vs %s mode=%s ratio=%.4f",
        filename_a,
        filename_b,
        mode,
        stats["diff_ratio"],
    )

    return {
        "comparison_id": comparison_id,
        "diff_image_url": f"/api/screenshot/compare/file/{comparison_id}.png",
        "mode": mode,
        "stats": stats,
        "file_a": {"job_id": job_id_a, "filename": filename_a},
        "file_b": {"job_id": job_id_b, "filename": filename_b},
        "output_path": str(out_path),
    }
