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

# Artifact generation meta-phrasing patterns that dilute semantic retrieval vectors
ARTIFACT_META_PATTERNS = [
    re.compile(
        r"^(?:please\s+)?(?:write|draft|create|generate|compile)\s+(?:a|an|the)?\s*(?:ship\s*30(?:\s*for\s*30)?(?:\s*atomic)?\s*essay|essay|markdown\s+summary|executive\s+summary|brief|overview|(?:interactive\s+)?(?:html(?:\s*css)?\s*card|html(?:\s*calculator)?\s*artifact|artifact|card))\s+(?:about|on|for|regarding|covering|explaining)?\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"\s*(?:as|in(?:to)?)\s+(?:a|an)\s+(?:ship\s*30(?:\s*for\s*30)?\s*essay|artifact|markdown\s+summary|html\s*card)\s*$",
        re.IGNORECASE,
    ),
]

import difflib
from app.retrieval.corpus_guests import CORPUS_GUESTS

# Build lookup mapping of canonical guest name tokens across all 301 corpus guests
_GUEST_NAME_TOKENS: dict[str, str] = {}
for _guest in CORPUS_GUESTS:
    for _w in re.findall(r"[A-Za-z]+", _guest):
        if len(_w) >= 3 and _w.lower() not in {"and", "the", "for", "with"}:
            _GUEST_NAME_TOKENS[_w.lower()] = _w


# Common domain vocabulary words that must NEVER be treated as guest name typos
COMMON_DOMAIN_WORDS = {
    "about", "above", "acquisition", "activation", "after", "again", "agent",
    "agents", "agile", "ai", "align", "alignment", "all", "also", "and", "angel",
    "any", "are", "arr", "back", "backlog", "because", "been", "before", "being",
    "below", "best", "between", "blog", "board", "both", "build", "building",
    "burn", "business", "cac", "can", "capital", "career", "churn", "code",
    "coding", "company", "consumer", "conversion", "could", "csat", "culture",
    "customer", "customers", "deliver", "delivery", "design", "designer",
    "designers", "designing", "development", "did", "direct", "director", "does",
    "doing", "down", "during", "each", "early", "engineering", "enterprise",
    "episode", "eval", "evals", "even", "every", "experience", "explain",
    "feedback", "find", "first", "flow", "flywheel", "founder", "founders",
    "founding", "framework", "from", "funnel", "further", "get", "getting",
    "give", "good", "great", "grow", "growth", "guide", "had", "has", "have",
    "having", "head", "help", "here", "high", "hire", "hiring", "how", "impact",
    "into", "investor", "investors", "just", "kanban", "know", "kpi", "kpis",
    "launch", "launching", "lead", "leader", "leadership", "learn", "learning",
    "lesson", "lessons", "level", "like", "llm", "look", "loop", "loops", "ltv",
    "make", "making", "manage", "management", "manager", "many", "market",
    "marketing", "meeting", "metric", "metrics", "mindset", "model", "monetization",
    "more", "most", "mrr", "much", "need", "new", "newsletter", "next", "nps",
    "now", "off", "okr", "okrs", "once", "one", "only", "onboarding", "operate",
    "operating", "operation", "peer", "people", "perf", "playbook", "plg",
    "podcast", "post", "pricing", "principal", "principle", "principles",
    "prioritization", "priority", "problem", "product", "products", "prompt",
    "rag", "report", "retention", "right", "roadmap", "roadmaps", "rule", "rules",
    "run", "running", "runway", "saas", "sales", "same", "say", "saying", "says",
    "scale", "scaling", "scrum", "search", "second", "seed", "series", "ship",
    "shipped", "shipping", "should", "show", "side", "skill", "skills", "slg",
    "software", "some", "sprint", "staff", "stakeholder", "stakeholders", "start",
    "startup", "startups", "strategy", "subscribers", "system", "systems", "tactic",
    "tactics", "take", "talk", "team", "teams", "tech", "technology", "tell",
    "than", "that", "the", "their", "them", "then", "there", "these", "they",
    "thing", "things", "think", "thinking", "this", "those", "through", "time",
    "tool", "tools", "track", "trait", "traits", "two", "under", "up", "use",
    "using", "value", "vector", "venture", "very", "viral", "virality", "want",
    "way", "well", "were", "what", "when", "where", "which", "while", "who",
    "why", "will", "with", "work", "working", "world", "would", "year", "years",
}


# Canonical guest roster without episode duplicate qualifiers (" 2.0", " Live", etc.)
CANONICAL_CORPUS_GUESTS: list[str] = []
for _g in CORPUS_GUESTS:
    _c = re.sub(r"\s+(?:Live|\d+\.\d+|\d+)$", "", _g, flags=re.IGNORECASE).strip()
    if _c and _c not in CANONICAL_CORPUS_GUESTS:
        CANONICAL_CORPUS_GUESTS.append(_c)

_GUESTS_BY_WORD_COUNT: dict[int, list[str]] = {}
for _cg in CANONICAL_CORPUS_GUESTS:
    _cnt = len(_cg.split())
    _GUESTS_BY_WORD_COUNT.setdefault(_cnt, []).append(_cg)


def normalize_guest_typos(text: str) -> str:
    """
    Fuzzy-correct typos and phonetic variations in guest names against the corpus guest roster.
    1. Evaluates 3-word and 2-word n-grams against canonical guest names of the corresponding length
       (e.g., 'Shreyash Doshi' -> 'Shreyas Doshi', 'Lauren Isford' -> 'Lauryn Isford').
       Preserves possessive suffixes and prevents redundant sub-token replacement on full guest names.
    2. Evaluates standalone capitalized name tokens (e.g. 'Shreyash' -> 'Shreyas', 'Cheskey' -> 'Chesky')
       while strictly preserving lowercase common vocabulary like 'mean' or 'mode' and PM domain terms.
    """
    cleaned = text
    words = re.findall(r"\b[A-Za-z]+\b", cleaned)

    # 1. Multi-word guest name matching by exact token count (3-gram, 2-gram)
    for n in (3, 2):
        if len(words) < n:
            continue
        g_list = _GUESTS_BY_WORD_COUNT.get(n, [])
        g_lowers = [g.lower() for g in g_list]
        for i in range(len(words) - n + 1):
            ngram = " ".join(words[i:i+n])
            if ngram.lower() in g_lowers:
                continue
            close = difflib.get_close_matches(ngram.lower(), g_lowers, n=1, cutoff=0.80)
            if close:
                target = next(g for g in g_list if g.lower() == close[0])
                if target.lower() in cleaned.lower():
                    continue
                pattern = r"\b" + r"\s+".join(re.escape(words[i+k]) for k in range(n)) + r"\b"
                cleaned = re.sub(pattern, target, cleaned, flags=re.IGNORECASE)

    # 2. Standalone capitalized token matching with strict length delta <= 1 and min len >= 5
    refreshed_words = re.findall(r"\b[A-Za-z]+\b", cleaned)
    token_keys = list(_GUEST_NAME_TOKENS.keys())
    for word in refreshed_words:
        # Require capitalization and length >= 5 for single-token guest matching
        if not word[0].isupper() or len(word) < 5:
            continue
        w_lower = word.lower()
        if w_lower in COMMON_DOMAIN_WORDS:
            continue
        if w_lower not in _GUEST_NAME_TOKENS:
            candidates = [t for t in token_keys if abs(len(w_lower) - len(t)) <= 1]
            matches = difflib.get_close_matches(w_lower, candidates, n=1, cutoff=0.82)
            if matches:
                correct_word = _GUEST_NAME_TOKENS[matches[0]]
                cleaned = re.sub(rf"\b{re.escape(word)}\b", correct_word, cleaned)

    return cleaned



def collapse_spaced_acronyms(text: str) -> str:
    """
    Collapse sequences of single uppercase letters separated by spaces or slashes (2 to 5 letters),
    with optional trailing plural 's', e.g. 'L N O' -> 'LNO', 'O K R s' -> 'OKRs', 'P M F' -> 'PMF'.
    """
    pattern = r"\b([A-Z])(?:\s*[/ ]\s*([A-Z])){1,4}(?:\s*([sS]))?\b"
    return re.sub(pattern, lambda m: re.sub(r"[\s/]", "", m.group(0)), text)



def normalize_query(query: str) -> str:
    """
    Normalize natural language search query for retrieval.
    Rejects empty or whitespace-only queries.
    Strips conversational podcast meta-phrasing and artifact generation prefixes
    to prevent vector dilution against non-domain boilerplate.
    Fuzzy-normalizes guest name typos and collapses spaced acronyms universally.
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

    # Strip artifact generation meta-framing if present
    for pat in ARTIFACT_META_PATTERNS:
        cleaned = pat.sub("", cleaned).strip()

    # Apply universal guest typo normalization
    cleaned = normalize_guest_typos(cleaned)

    # Collapse spaced or slash-delimited uppercase acronym letters
    cleaned = collapse_spaced_acronyms(cleaned)

    if cleaned:
        text = cleaned

    return text
