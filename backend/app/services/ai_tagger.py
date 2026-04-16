"""AI Image Tagger — zero-shot classification using OpenCLIP.

Lazy-loads the model on first call (downloads weights ~350 MB on first run).
Runs inference on CPU in a thread pool to avoid blocking the event loop.
"""
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional

import torch
from PIL import Image

# Lazy globals — set on first call to _ensure_model()
_model = None
_preprocess = None
_tokenizer = None
_device = "cpu"
_MODEL_NAME = "ViT-B-32"
_PRETRAINED = "laion2b_s34b_b79k"


def _ensure_model():
    global _model, _preprocess, _tokenizer
    if _model is not None:
        return
    import open_clip  # heavy import, defer

    _model, _, _preprocess = open_clip.create_model_and_transforms(
        _MODEL_NAME, pretrained=_PRETRAINED, device=_device
    )
    _tokenizer = open_clip.get_tokenizer(_MODEL_NAME)
    _model.eval()


def _load_image(path: Path) -> Optional[Image.Image]:
    try:
        img = Image.open(path).convert("RGB")
        return img
    except Exception:
        return None


def _score_image(image_path: Path, labels: list[str]) -> dict[str, float]:
    """Return {label: probability} for one image against a list of text labels."""
    _ensure_model()
    img = _load_image(image_path)
    if img is None:
        return {}

    image_input = _preprocess(img).unsqueeze(0).to(_device)
    text_tokens = _tokenizer(labels).to(_device)

    with torch.no_grad():
        image_features = _model.encode_image(image_input)
        text_features = _model.encode_text(text_tokens)

        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        similarities = (image_features @ text_features.T).squeeze(0)
        probs = similarities.softmax(dim=-1).cpu().tolist()

    return {label: round(prob, 4) for label, prob in zip(labels, probs)}


def tag_images_sync(
    image_paths: list[Path],
    labels: list[str],
    on_progress: Optional[callable] = None,
) -> list[dict]:
    """Synchronous batch tagger — called from thread.

    Returns list of {path, scores: {label: prob}, top_tag, top_score}.
    """
    _ensure_model()
    results = []
    total = len(image_paths)
    for i, path in enumerate(image_paths):
        scores = _score_image(path, labels)
        top_tag = max(scores, key=scores.get) if scores else None
        top_score = scores.get(top_tag, 0) if top_tag else 0
        results.append({
            "path": str(path),
            "filename": path.name,
            "scores": scores,
            "top_tag": top_tag,
            "top_score": top_score,
        })
        if on_progress:
            on_progress(i + 1, total, path.name, top_tag, top_score)
    return results


async def tag_images_async(
    image_paths: list[Path],
    labels: list[str],
    on_progress=None,
) -> list[dict]:
    """Run tagging in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(
        tag_images_sync, image_paths, labels, on_progress
    )
