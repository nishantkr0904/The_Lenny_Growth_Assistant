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


# Conversational meta-phrasing patterns that artificially match transcript outro/intro boilerplate
PODCAST_META_PATTERNS = [
    re.compile(
        r"^(?:what\s+(?:does|did)\s+)?(?:lenny(?:\'s)?(?:\s+podcast)?|the\s+podcast)\s+(?:say|think|mention|discuss|have\s+to\s+say)(?:\s+about)?\s*[:\-,]?\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:does|did)\s+(?:lenny(?:\'s)?(?:\s+podcast)?|the\s+podcast)\s+(?:say|think|mention|discuss|cover|talk\s+about)\s+(?:anything\s+about\s+)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:what\s+is\s+said\s+(?:in|on)\s+(?:lenny(?:\'s)?(?:\s+podcast)?|the\s+podcast)\s+about\s+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:in|on)\s+(?:lenny(?:\'s)?(?:\s+podcast)?|the\s+podcast),?\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"\s*(?:in|on)\s+lenny(?:\'s)?(?:\s+podcast)?\??$",
        re.IGNORECASE,
    ),
]


def normalize_query(query: str) -> str:
    """
    Normalize natural language search query for retrieval.
    Rejects empty or whitespace-only queries.
    Strips conversational podcast meta-phrasing to prevent false matches
    against intro/outro podcast boilerplate.
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

    # Strip conversational podcast meta-framing if present
    cleaned = text
    for pat in PODCAST_META_PATTERNS:
        cleaned = pat.sub("", cleaned).strip()

    if cleaned:
        text = cleaned

    return text

