"""Heuristic topic classifier for legislative propositions."""

import re
from dataclasses import dataclass

from app.classification.rules import TOPIC_RULES


@dataclass
class TopicMatch:
    slug: str
    confianca: float
    keywords_matched: list[str]


def classify_proposicao(
    ementa: str,
    tipo: str | None = None,
    min_confianca: float = 0.05,
) -> list[TopicMatch]:
    """Classify a proposição by its ementa text.

    Returns topics sorted by confidence score (descending).
    Multiple topics per proposição are expected.
    """
    ementa_lower = _normalize_text(ementa)
    results = []

    for slug, keywords in TOPIC_RULES.items():
        matched = []
        for keyword in keywords:
            keyword_lower = _normalize_text(keyword)
            if re.search(re.escape(keyword_lower), ementa_lower):
                matched.append(keyword)

        if not matched:
            continue

        # Confidence: ratio of matched keywords to total, with diminishing returns
        raw_score = len(matched) / len(keywords)
        # Boost for multiple matches (more confident with more evidence)
        confianca = min(1.0, raw_score * (1 + 0.2 * len(matched)))

        if confianca >= min_confianca:
            results.append(
                TopicMatch(
                    slug=slug,
                    confianca=round(confianca, 3),
                    keywords_matched=matched,
                )
            )

    results.sort(key=lambda x: x.confianca, reverse=True)
    return results


def _normalize_text(text: str) -> str:
    """Normalize text for matching: lowercase, remove accents."""
    text = text.lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ü": "u",
        "ç": "c",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text
