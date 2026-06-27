# services/similarity_service.py
import math
from typing import List

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes the cosine similarity between two numeric vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(b * b for b in v2))
    if not magnitude_v1 or not magnitude_v2:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)
