"""Conversational Intent Classifier.

Deterministically routes incoming user messages to either:
1. Casual/conversational intent (greetings, pleasantries, gratitude, farewells) -> lightweight conversational response
2. Knowledge/research intent -> authoritative query rewriting, Pi agent, vector retrieval, and Grounding Gate
"""

from enum import Enum
import re
from typing import NamedTuple


class IntentCategory(str, Enum):
    """Broad classification categories for user turns."""
    CONVERSATIONAL = "conversational"
    KNOWLEDGE = "knowledge"


class IntentDecision(NamedTuple):
    """Decision outcome from intent analysis."""
    category: IntentCategory
    sub_intent: str  # e.g., 'greeting', 'gratitude', 'farewell', 'pleasantry', 'knowledge_query'
    is_conversational: bool


# Canonical patterns for conversational intents
# These represent low-information social interactions without an underlying knowledge target.
GREETING_PATTERN = re.compile(
    r"^(?:hi|hello|hey|hiya|howdy|greetings|welcome|yo|hola|"
    r"good\s+(?:morning|afternoon|evening|day))(?:\s+(?:there|lenny(?:\s+assistant)?|bot|friend|all))?[!.]*$",
    re.IGNORECASE,
)

GRATITUDE_PATTERN = re.compile(
    r"^(?:thanks|thank\s+you(?:\s+so\s+much|\s+very\s+much)?|many\s+thanks|"
    r"appreciate\s+it|much\s+appreciated|thx|ty|cheers)[!.]*$",
    re.IGNORECASE,
)

FAREWELL_PATTERN = re.compile(
    r"^(?:bye|goodbye|bye\s+bye|see\s+you(?:\s+later|\s+soon)?|see\s+ya|"
    r"take\s+care|farewell|have\s+a\s+good\s+(?:day|one|evening|night))[!.]*$",
    re.IGNORECASE,
)

PLEASANTRY_PATTERN = re.compile(
    r"^(?:how\s+are\s+you(?:\s+doing|\s+today)?|how's\s+it\s+going|"
    r"how\s+is\s+it\s+going|what's\s+up|what\s+is\s+up|sup)[?!.]*$",
    re.IGNORECASE,
)

CAPABILITY_PATTERN = re.compile(
    r"^(?:who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do|"
    r"help(?:\s+me)?|how\s+do\s+you\s+work|what\s+is\s+this(?:\s+app)?)[?!.]*$",
    re.IGNORECASE,
)

ACKNOWLEDGMENT_PATTERN = re.compile(
    r"^(?:ok|okay|cool|great|awesome|understood|got\s+it|sounds\s+good|perfect|nice)[!.]*$",
    re.IGNORECASE,
)

# High-confidence substantive indicators that force KNOWLEDGE intent
SUBSTANTIVE_KEYWORDS = re.compile(
    r"\b(?:lno|plg|pmf|cac|ltv|nps|arr|mrr|roi|okr|kpi|icp|b2b|b2c|seo|gtm|"
    r"framework|pricing|retention|churn|activation|onboarding|acquisition|"
    r"growth|product|strategy|pm|roadmap|experiment|metric|pre-?mortem|"
    r"lenny|shreyas|doshi|elena|verna|hila|qu|adam|fishman|brian|chesky|"
    r"transcript|podcast|episode|interview|guest|quote|quantum)\b",
    re.IGNORECASE,
)

SUBSTANTIVE_QUERY_PREFIXES = re.compile(
    r"\b(?:what\s+is|what\s+does|what\s+did|what\s+are|how\s+to|how\s+do|how\s+does|"
    r"why\s+did|why\s+is|why\s+do|who\s+is|who\s+was|tell\s+me\s+about|"
    r"explain|describe|summarize|give\s+me|compare|write\s+a|generate|create)\b",
    re.IGNORECASE,
)


def classify_conversational_intent(text: str) -> IntentDecision:
    """
    Classify whether a user input is a pure conversational turn or a knowledge query.
    
    Rules:
    1. If the message contains substantive domain terms or question prefixes targeting
       external knowledge, it is ALWAYS classified as KNOWLEDGE.
    2. If the message matches standard conversational intents (greetings, gratitude,
       farewells, pleasantries, capabilities, acknowledgments) without substantive payload,
       it is classified as CONVERSATIONAL.
    3. Compound messages (e.g., "Hi, what does Shreyas Doshi say about LNO?") are strictly
       classified as KNOWLEDGE.
    4. Anything ambiguous or longer than ~15 words is routed to KNOWLEDGE to prevent false negatives.
    """
    cleaned = text.strip()
    if not cleaned:
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="empty",
            is_conversational=True,
        )

    # Normalize whitespace for pattern evaluation
    normalized = " ".join(cleaned.split())

    # Fast-path: Check for substantive keywords or question patterns targeting knowledge
    if SUBSTANTIVE_KEYWORDS.search(normalized):
        return IntentDecision(
            category=IntentCategory.KNOWLEDGE,
            sub_intent="knowledge_keyword",
            is_conversational=False,
        )

    # If message contains information-seeking query structures
    # (unless it's a known pure social inquiry like "how are you" or "who are you")
    if SUBSTANTIVE_QUERY_PREFIXES.search(normalized):
        # Exclude pure social inquiry matches
        if not PLEASANTRY_PATTERN.match(normalized) and not CAPABILITY_PATTERN.match(normalized):
            return IntentDecision(
                category=IntentCategory.KNOWLEDGE,
                sub_intent="query_structure",
                is_conversational=False,
            )

    # Length guard: Conversational turns are concise. Long inputs are treated as knowledge/context.
    token_count = len(normalized.split())
    if token_count > 15:
        return IntentDecision(
            category=IntentCategory.KNOWLEDGE,
            sub_intent="length_threshold",
            is_conversational=False,
        )

    # Check specific conversational patterns
    if GREETING_PATTERN.match(normalized):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="greeting",
            is_conversational=True,
        )

    if GRATITUDE_PATTERN.match(normalized):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="gratitude",
            is_conversational=True,
        )

    if PLEASANTRY_PATTERN.match(normalized):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="pleasantry",
            is_conversational=True,
        )

    if FAREWELL_PATTERN.match(normalized):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="farewell",
            is_conversational=True,
        )

    if CAPABILITY_PATTERN.match(normalized):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="capability",
            is_conversational=True,
        )

    if ACKNOWLEDGMENT_PATTERN.match(normalized):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="acknowledgment",
            is_conversational=True,
        )

    # Check for simple greeting combinations, e.g. "Hey there! How are you?" or "okay, got it"
    parts = [p.strip() for p in re.split(r"[,.!?;]+", normalized) if p.strip()]
    if parts and all(
        GREETING_PATTERN.match(p)
        or GRATITUDE_PATTERN.match(p)
        or PLEASANTRY_PATTERN.match(p)
        or FAREWELL_PATTERN.match(p)
        or CAPABILITY_PATTERN.match(p)
        or ACKNOWLEDGMENT_PATTERN.match(p)
        for p in parts
    ):
        return IntentDecision(
            category=IntentCategory.CONVERSATIONAL,
            sub_intent="composite_conversational",
            is_conversational=True,
        )

    # Default fallback: If not explicitly recognized as conversational, route to knowledge
    return IntentDecision(
        category=IntentCategory.KNOWLEDGE,
        sub_intent="default_knowledge",
        is_conversational=False,
    )
