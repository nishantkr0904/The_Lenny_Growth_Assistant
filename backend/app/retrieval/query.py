"""Query normalization and boundary processing for vector retrieval."""

import re

# Character replacements for query normalization
UNICODE_QUERY_REPLACEMENTS = [
    ("\u2018", "'"),
    ("\u2019", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2013", "-"),
    ("\u2014", "--"),
    ("\u00a0", " "),
    ("\u2026", "..."),
]


def normalize_query(query: str) -> str:
    """
    Normalize natural language search query for retrieval.
    Rejects empty or whitespace-only queries.
    """
    if not query:
        raise ValueError("Search query cannot be empty")

    text = query.strip()
    for old, new in UNICODE_QUERY_REPLACEMENTS:
        text = text.replace(old, new)

    # Collapse excessive internal whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise ValueError("Search query cannot be empty or contain only whitespace")

    return text
