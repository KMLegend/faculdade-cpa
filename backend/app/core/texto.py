"""Normalização de texto — função única, usada por importador e matching (doc 02)."""

import re
import unicodedata


def slugificar(texto: str) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços colapsados.

    'Profa Victória' -> 'profa victoria'

    ⚠️ NÃO resolve typos: 'washignton' != 'washington'. Para isso, o fuzzy
    matching do doc 03 §4.
    """
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()
