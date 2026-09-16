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
        """Compile a structured Markdown research brief grounded exclusively in evidence."""
        lines = [
            f"# {title}",
            "",
            "> **Research Brief** · Compiled from Lenny's Podcast Transcripts",
            "",
            "## Executive Summary",
            "",
            content.strip(),
            "",
        ]
        lines.extend([
            "## Key Strategic Insights",
            "",
        ])

        paragraphs = [p.strip() for p in content.strip().split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            for p in paragraphs[1:]:
                lines.append(p if p.startswith("-") or p.startswith("*") else f"- {p}")
        elif paragraphs:
            lines.append(f"- {paragraphs[0]}")
        lines.extend([
            "",
            "## Source Citations & Provenance",
            "",
        ])

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
            f"Most founders and operators treat {topic.lower() if topic else 'product growth'} through intuition or trial and error. "
            "They focus on downstream execution without establishing clear mental models or foundational decision criteria.",
            "",
            "**Here is the core truth: Frameworks from battle-tested operators exist to prevent wasted motion.**",
            "",
            f"When {primary_guest} sat down with Lenny Rachitsky on *{episode_title}*, they broke down the practical reality "
            "of how high-impact teams operate under real-world constraints.",
            "",
            "---",
            "",
            "## 2. Core Insights & Evidence",
            "",
        ]

        if primary_quote:
            essay_sections.extend([
                f"> \"{primary_quote.strip()}\"",
                f"> — **{primary_guest}**, *{episode_title}*",
                "",
            ])

        essay_sections.extend([
            "## 3. The Tactical Playbook",
            "",
            content.strip(),
            "",
            "---",
            "",
            "## 4. Actionable Takeaway: What to Do on Monday Morning",
            "",
            f"Implementing insights from {primary_guest} requires deliberate execution:",
            "",
            "1. **Audit current practices** against the principles discussed above.",
            "2. **Identify immediate high-impact areas** where these findings apply directly to your team or product priorities.",
            "3. **Align cross-functional stakeholders** to ensure shared context across your organization.",
            "",
            "Grounded insights from experienced leaders save months of misdirected effort. Commit to the principles and execute.",
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
