"""Shannon entropy calculation - flags packed/encrypted content."""
from __future__ import annotations

import math
from collections import Counter


def calculate_entropy(data: bytes) -> float:
    """Shannon entropy 0.0 - 8.0. >7.2 = packed/encrypted likely."""
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    entropy = 0.0
    for c in counts.values():
        p = c / total
        entropy -= p * math.log2(p)
    return round(entropy, 4)


def classify_entropy(value: float) -> str:
    """Returns: plain | mixed | compressed | packed_or_encrypted"""
    if value < 4.5:
        return "plain"
    if value < 6.5:
        return "mixed"
    if value < 7.2:
        return "compressed"
    return "packed_or_encrypted"
