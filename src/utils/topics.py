"""Shared utilities for community topic normalization and ranking."""

from collections import Counter
import re
import unicodedata


# Spanish "-es" plurals whose singular ends in a consonant.
# These forms cannot safely be handled by a generic suffix rule.
_ES_PLURALS = {
    "errores": "error",
    "servidores": "servidor",
    "procesadores": "procesador",
    "monitores": "monitor",
    "generadores": "generador",
    "contenedores": "contenedor",
    "accesores": "accesor",
    "mujeres": "mujer",
    "papeles": "papel",
    "relojes": "reloj",
    "paneles": "panel",
    "perfiles": "perfil",
    "jardines": "jardín",
}

_INVARIABLE_WORDS = {
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "crisis",
    "tesis",
    "dosis",
    "análisis",
    "paréntesis",
}


def _normalize_word(word: str) -> str:
    """Normalize common Spanish plural forms to singular."""
    if word.endswith("iones") and len(word) > 6:
        return word[:-5] + "ión"

    if word in _INVARIABLE_WORDS:
        return word

    if word in _ES_PLURALS:
        return _ES_PLURALS[word]

    # Remove the final "s" only when the resulting word ends in a vowel.
    # This preserves forms such as "serie" from "series".
    if word.endswith("s") and len(word) > 4:
        singular_candidate = word[:-1]
        if singular_candidate[-1] in "aeiouáéíóúü":
            return singular_candidate

    return word


def _normalize_label(topic: str) -> str:
    """Return a lowercase label with recognized plural words singularized."""
    label = topic.strip().lower()
    return re.sub(
        r"[a-záéíóúüñ]+",
        lambda match: _normalize_word(match.group(0)),
        label,
    )


def _normalize_key(topic: str) -> str:
    """Return a lowercase, accent-free key for grouping equivalent topics."""
    normalized = unicodedata.normalize("NFD", _normalize_label(topic))
    return "".join(
        char
        for char in normalized
        if unicodedata.category(char) != "Mn"
    )


def rank_topics(
    topics: list[str],
    top_n: int | None = None,
) -> list[tuple[str, int]]:
    """Normalize topics, rank by frequency, and optionally limit the result.

    Labels use the normalized singular form when a recognized plural occurs.
    Ties are broken alphabetically by the normalized grouping key.
    """
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}

    for topic in topics:
        if not isinstance(topic, str) or not topic.strip():
            continue

        label = _normalize_label(topic)
        key = _normalize_key(label)

        if key not in labels:
            labels[key] = label

        counts[key] += 1

    ranked = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0]),
    )

    if top_n is not None:
        ranked = ranked[:top_n]

    return [
        (labels[key], count)
        for key, count in ranked
    ]
