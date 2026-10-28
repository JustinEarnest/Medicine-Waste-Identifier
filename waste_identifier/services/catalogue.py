"""
Medicine catalogue matching service for Medicine Waste Identifier.
Implements Phase 2 normalization and deterministic catalogue lookup (plan.md).
"""
import re
import json
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CATALOGUE_PATH = BASE_DIR / "dataset" / "cleaned_catalogue.json"

_CATALOGUE_RECORDS: Optional[List[Dict[str, Any]]] = None
_NORMALIZED_INDEX: Optional[Dict[str, Dict[str, Any]]] = None


def normalize_string(text: str) -> str:
    """Strips punctuation and standardizes whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    return ' '.join(cleaned.split()).lower()


def load_catalogue() -> List[Dict[str, Any]]:
    """Loads and caches the cleaned medicine catalogue."""
    global _CATALOGUE_RECORDS, _NORMALIZED_INDEX
    if _CATALOGUE_RECORDS is not None:
        return _CATALOGUE_RECORDS

    if not CATALOGUE_PATH.exists():
        _CATALOGUE_RECORDS = []
        _NORMALIZED_INDEX = {}
        return _CATALOGUE_RECORDS

    with open(CATALOGUE_PATH, "r", encoding="utf-8") as f:
        _CATALOGUE_RECORDS = json.load(f)

    _NORMALIZED_INDEX = {}
    for item in _CATALOGUE_RECORDS:
        norm = item.get("normalized_name", "")
        if norm and norm not in _NORMALIZED_INDEX:
            _NORMALIZED_INDEX[norm] = item

    return _CATALOGUE_RECORDS


def string_similarity(a: str, b: str) -> float:
    """Returns ratio between two normalized strings."""
    return SequenceMatcher(None, a, b).ratio()


def match_catalogue(
    candidate_name: Optional[str],
    manufacturer: Optional[str] = None,
    strength: Optional[str] = None,
    min_similarity: float = 0.65,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Matches candidate medicine details against the Indian Medicines Catalogue.
    Returns best match, candidate list, and confidence.
    """
    records = load_catalogue()
    if not candidate_name or not records:
        return {
            "match": None,
            "candidates": [],
            "confidence": 0.0,
            "status": "unconfirmed",
            "reason": "No readable medicine name provided."
        }

    norm_query = normalize_string(candidate_name)
    query_tokens = set(norm_query.split())

    # 1. Exact match check
    if _NORMALIZED_INDEX and norm_query in _NORMALIZED_INDEX:
        exact = _NORMALIZED_INDEX[norm_query]
        return {
            "match": exact,
            "candidates": [exact],
            "confidence": 1.0,
            "status": "confirmed",
            "reason": "Exact catalogue match found."
        }

    # 2. Token overlap and similarity scoring
    scored_candidates: List[Tuple[float, Dict[str, Any]]] = []

    for item in records:
        norm_item = item.get("normalized_name", "")
        item_tokens = set(norm_item.split())

        # Quick token check for performance
        overlap = len(query_tokens.intersection(item_tokens))
        if overlap == 0 and len(norm_query) > 3 and norm_query not in norm_item:
            continue

        sim = string_similarity(norm_query, norm_item)
        score = sim

        # Bonus for token subset match
        if query_tokens.issubset(item_tokens) or item_tokens.issubset(query_tokens):
            score += 0.15

        # Bonus for manufacturer match if provided
        if manufacturer:
            norm_mfr = normalize_string(manufacturer)
            item_mfr = item.get("normalized_manufacturer", "")
            if norm_mfr and (norm_mfr in item_mfr or item_mfr in norm_mfr):
                score += 0.15

        # Bonus for matching strength if provided
        if strength and strength.lower() in norm_item:
            score += 0.10

        score = min(1.0, score)
        if score >= min_similarity:
            scored_candidates.append((score, item))

    if not scored_candidates:
        return {
            "match": None,
            "candidates": [],
            "confidence": 0.0,
            "status": "unconfirmed",
            "reason": "No matching catalogue entries found with sufficient similarity."
        }

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_item = scored_candidates[0]
    top_items = [c[1] for c in scored_candidates[:top_k]]

    if best_score >= 0.82:
        status = "confirmed"
        reason = f"High-confidence catalogue match ({best_score:.2f})."
    elif best_score >= 0.68:
        status = "ambiguous"
        reason = f"Moderate match ({best_score:.2f}); user verification recommended."
    else:
        status = "unconfirmed"
        reason = f"Low confidence match ({best_score:.2f}); needs clearer image."

    return {
        "match": best_item if status != "unconfirmed" else None,
        "candidates": top_items,
        "confidence": round(best_score, 3),
        "status": status,
        "reason": reason
    }
