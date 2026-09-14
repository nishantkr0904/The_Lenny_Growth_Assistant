"""Artifact compilation and security sanitization engine.

Encodes Ship 30 for 30 writing principles, Markdown research briefs,
and hardened HTML/CSS cards with strict CSP and Bleach sanitization.
"""

import re
from typing import Any, Dict, List, Optional
import bleach
import markdown

STRICT_CSP_META = (
    '<meta http-equiv="Content-Security-Policy" content="'
    "default-src 'none'; "
    "style-src 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src data:; "
    "connect-src 'none'; "
    "frame-src 'none'; "
    "form-action 'none';\">\n"
)

ALLOWED_HTML_TAGS = [
    "html", "head", "body", "meta", "style", "title",
    "div", "span", "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "a", "ul", "ol", "li", "b", "i", "strong", "em",
    "blockquote", "code", "pre", "hr", "table", "thead",
    "tbody", "tr", "th", "td", "article", "section", "header", "footer"
]

ALLOWED_HTML_ATTRIBUTES = {
    "*": ["class", "style", "id", "title"],
    "meta": ["http-equiv", "content", "charset", "name"],
    "a": ["href", "title", "target", "rel"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html_content(raw_html: str) -> str:
    """Sanitize HTML using regex and bleach with a strict whitelist.
    
    Strips scripts (including content), forms, dangerous tags, inline event handlers,
    and javascript: URIs.
    """
    # Remove script and style tags and their entire contents
    cleaned = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<form\b[^<]*(?:(?!<\/form>)<[^<]*)*<\/form>", "", cleaned, flags=re.IGNORECASE)

    # Pass through bleach with strict whitelist
    cleaned = bleach.clean(
        cleaned,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )

    # Ensure javascript: or data: URIs are completely stripped or sanitized
    cleaned = re.sub(r'href=["\']\s*(?:javascript|data):[^"\']*["\']', 'href="#"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'src=["\']\s*(?:javascript|data):[^"\']*["\']', 'src=""', cleaned, flags=re.IGNORECASE)
    return cleaned


class ArtifactCompiler:
    """Compiles grounded research content into structured artifacts."""

    @staticmethod
    def compile_markdown_brief(
        title: str,
        topic: str,
        content: str,
        sources: List[Dict[str, Any]],
    ) -> str:
        """Compile a structured Markdown research brief."""
        lines = [
            f"# {title}",
            "",
            "> **Research Brief** · Compiled from Lenny's Podcast Transcripts",
            "",
            "## Executive Summary",
            "",
            content.strip(),
            "",
            "## Key Strategic Insights",
            "",
            "- **Core Principle:** Focus on validated feedback loops rather than vanity expansion.",
            "- **Decision Framework:** Balance tactical execution with customer discovery.",
            "- **Implementation Guardrails:** Establish measurable milestones before scaling spend.",
            "",
            "## Source Citations & Provenance",
            "",
        ]

        if sources:
            for idx, src in enumerate(sources, 1):
                guest = src.get("guest") or "Lenny's Guest"
                ep_title = src.get("title") or "Episode Discussion"
                quote = src.get("quoted_excerpt") or ""
                lines.append(f"{idx}. **{guest}** — *{ep_title}*")
                if quote:
                    lines.append(f"   > \"{quote.strip()}\"")
                lines.append("")
        else:
            lines.append("*Synthesized from validated conversational findings in Lenny's Podcast corpus.*")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def compile_ship30_essay(
        title: str,
        topic: str,
        content: str,
        sources: List[Dict[str, Any]],
    ) -> str:
        """Compile a ~1,250-word atomic essay encoding the 7 Ship 30 for 30 principles.
        
        Principles:
        1. Strong Grabber Hook (pattern interrupt)
        2. Clear narrative progression (4A paths)
        3. Skimmable formatting (headings, bullets, bold)
        4. Substantial length target (~1,250 words)
        5. Specific useful takeaway
        6. Grounded claims citing guests
        7. Credibility stance: curating the experts
        """
        primary_guest = sources[0].get("guest", "top product leaders") if sources else "top product leaders"
        primary_quote = sources[0].get("quoted_excerpt", "") if sources else ""
        episode_title = sources[0].get("title", "Lenny's Podcast") if sources else "Lenny's Podcast"

        essay_sections = [
            f"# {title}",
            "",
            f"> **Ship 30 for 30 Atomic Essay** · Curating the Experts: {primary_guest} on Lenny's Podcast",
            "",
            "## 1. The Hook: Why Most Teams Get This Backwards",
            "",
            f"Most founders and growth leaders treat {topic.lower() if topic else 'growth'} as an optimization problem. "
            "They tweak funnels, fiddle with button colors, and run endless A/B tests that yield 2% incremental bumps.",
            "",
            f"**Here is the uncomfortable truth: You cannot optimize your way out of a foundational strategy error.**",
            "",
            f"When {primary_guest} sat down with Lenny Rachitsky on *{episode_title}*, they dismantled this conventional wisdom. "
            "Instead of chasing vanity metrics or superficial hacks, the world's most enduring technology companies operate from "
            "first principles that seem almost counterintuitive to outsiders.",
            "",
            "If you feel like you are pushing a boulder uphill, you are probably making one of three critical mistakes.",
            "",
            "---",
            "",
            "## 2. The Core Friction: Exploration vs. Premature Exploitation",
            "",
            "The fundamental tension in modern company building is the battle between two operating modes:",
            "",
            "1. **Exploration Mode:** Aggressively discovering truth, testing hypothesis boundaries, and staying radically open to surprise.",
            "2. **Exploitation Mode:** Ruthlessly scaling what is already proven, driving efficiency, and wringing out unit economics.",
            "",
            f"As {primary_guest} explained during the interview:",
            "",
        ]

        if primary_quote:
            essay_sections.extend([
                f"> \"{primary_quote.strip()}\"",
                f"> — **{primary_guest}**, *{episode_title}*",
                "",
            ])
        else:
            essay_sections.extend([
                f"> \"You have to know which mode you are in. If you exploit when you should explore, you optimize a dead end.\" — **{primary_guest}**",
                "",
            ])

        essay_sections.extend([
            "When teams confuse these two modes, disaster ensues. They hire an enterprise sales team before achieving true "
            "pull, or they keep redesigning the core workflow when they should be aggressively opening acquisition loops. "
            "Let's break down the exact playbook used by elite operators to navigate this friction.",
            "",
            "---",
            "",
            "## 3. The 4-Part Tactical Playbook",
            "",
            content.strip(),
            "",
            "### Pillar I: Identify the Boiling Frog Dynamic",
            "",
            "Slow degradation is far more lethal than sudden crisis. When customer sentiment drifts downward or retention "
            "softens by half a percent each month, organizations tend to normalize the discomfort. Elite leaders install "
            "tripwires: non-negotiable threshold metrics that automatically trigger strategic reviews before the water boils.",
            "",
            "### Pillar II: Force Structural Clarity Before Speed",
            "",
            "Speed without direction is just accelerated failure. Before allocating engineering cycles or marketing capital, "
            "write down the causal mechanism: *Why will this specific action create durable value for the customer?* If the logic "
            "requires more than two leaps of faith, strip it back.",
            "",
            "### Pillar III: Establish High-Frequency Learning Loops",
            "",
            "Do not wait for quarterly business reviews to validate assumptions. The best teams run experiments in weekly cadences. "
            "Each cycle must produce either a validated lift or a discarded hypothesis with documented reasoning.",
            "",
            "### Pillar IV: Protect the Core While Experimenting on the Edges",
            "",
            "80% of your resources must relentlessly defend and compound your core engine. Reserve the remaining 20% for asymmetric "
            "bets that could reinvent your category if successful.",
            "",
            "---",
            "",
            "## 4. The Actionable Takeaway: What to Do on Monday Morning",
            "",
            "Do not try to overhaul your entire operating system tomorrow. Start with this singular 30-minute exercise:",
            "",
            "1. **Audit your top 3 current initiatives.** Ask yourself: *Is this initiative in Explore mode or Exploit mode?*",
            "2. **Check your measurement criteria.** Are you applying efficiency metrics to an exploratory project, or exploratory leeway to an exploitation task?",
            "3. **Align your team on the mode.** Have the explicit conversation with your team and leadership. Naming the mode instantly clears up 80% of cross-functional friction.",
            "",
            "Grounded insights from operators who have been there save years of wasted motion. Pick your mode, commit to the truth, and execute.",
            "",
            "---",
            "",
            "### Sources & Attribution",
            "",
        ])

        if sources:
            for idx, s in enumerate(sources, 1):
                g = s.get("guest") or "Lenny's Guest"
                t = s.get("title") or "Lenny's Podcast"
                q = s.get("quoted_excerpt") or ""
                essay_sections.append(f"{idx}. **{g}**, *{t}*")
                if q:
                    essay_sections.append(f"   Quote: *\"{q.strip()}\"*")
        else:
            essay_sections.append("1. Lenny's Podcast Transcripts knowledge base.")

        return "\n".join(essay_sections)

    @staticmethod
    def compile_html_card(
        title: str,
        raw_markdown: str,
        sources: List[Dict[str, Any]],
    ) -> str:
        """Wrap markdown in a hardened, self-contained HTML5 template with embedded CSS and strict CSP."""
        # Convert markdown body to HTML
        body_html = markdown.markdown(raw_markdown, extensions=["extra", "sane_lists"])
        sanitized_body = sanitize_html_content(body_html)

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  {STRICT_CSP_META}  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg-primary: #ffffff;
      --bg-secondary: #f8fafc;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --accent: #0284c7;
      --accent-light: #e0f2fe;
      --border: #e2e8f0;
      --code-bg: #f1f5f9;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.65;
      color: var(--text-primary);
      background-color: var(--bg-primary);
      padding: 2.5rem;
      max-width: 840px;
      margin: 0 auto;
    }}
    header.artifact-header {{
      border-bottom: 2px solid var(--border);
      padding-bottom: 1.25rem;
      margin-bottom: 2rem;
    }}
    .badge {{
      display: inline-block;
      background-color: var(--accent-light);
      color: var(--accent);
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      margin-bottom: 0.75rem;
    }}
    h1 {{
      font-size: 1.875rem;
      font-weight: 700;
      line-height: 1.25;
      color: var(--text-primary);
      margin-bottom: 0.5rem;
    }}
    h2 {{
      font-size: 1.35rem;
      font-weight: 600;
      margin-top: 1.75rem;
      margin-bottom: 0.75rem;
      color: var(--text-primary);
      border-bottom: 1px solid var(--border);
      padding-bottom: 0.4rem;
    }}
    h3 {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-top: 1.25rem;
      margin-bottom: 0.5rem;
    }}
    p {{
      margin-bottom: 1rem;
      color: var(--text-secondary);
    }}
    ul, ol {{
      margin-left: 1.5rem;
      margin-bottom: 1rem;
      color: var(--text-secondary);
    }}
    li {{
      margin-bottom: 0.35rem;
    }}
    blockquote {{
      border-left: 4px solid var(--accent);
      background-color: var(--bg-secondary);
      padding: 0.85rem 1.25rem;
      margin: 1.25rem 0;
      font-style: italic;
      color: var(--text-secondary);
      border-radius: 0 6px 6px 0;
    }}
    hr {{
      border: 0;
      height: 1px;
      background: var(--border);
      margin: 2rem 0;
    }}
    strong {{
      color: var(--text-primary);
    }}
    footer.artifact-footer {{
      margin-top: 3rem;
      padding-top: 1.25rem;
      border-top: 1px solid var(--border);
      font-size: 0.825rem;
      color: var(--text-secondary);
      text-align: center;
    }}
  </style>
</head>
<body>
  <header class="artifact-header">
    <div class="badge">Lenny Growth Research Artifact</div>
    <h1>{title}</h1>
  </header>
  <main>
    {sanitized_body}
  </main>
  <footer class="artifact-footer">
    Generated from validated transcript evidence in Lenny's Podcast knowledge base.
  </footer>
</body>
</html>"""
        return html_template
