"""Security tests verifying HTML sanitization and CSP enforcement."""

import pytest
from app.artifacts.compiler import ArtifactCompiler, sanitize_html_content, STRICT_CSP_META


def test_sanitize_html_strips_script_tags():
    malicious = "<p>Normal text</p><script>alert('xss')</script><b>Bold</b>"
    cleaned = sanitize_html_content(malicious)
    assert "<script>" not in cleaned
    assert "alert('xss')" not in cleaned
    assert "<p>Normal text</p>" in cleaned
    assert "<b>Bold</b>" in cleaned


def test_sanitize_html_strips_inline_event_handlers():
    malicious = '<div onclick="stealTokens()" onmouseover="evil()" onload="exploit()">Content</div>'
    cleaned = sanitize_html_content(malicious)
    assert "onclick" not in cleaned
    assert "onmouseover" not in cleaned
    assert "onload" not in cleaned
    assert "stealTokens" not in cleaned
    assert "Content</div>" in cleaned


def test_sanitize_html_neutralizes_javascript_uris():
    malicious = '<a href="javascript:alert(1)">Click me</a>'
    cleaned = sanitize_html_content(malicious)
    assert "javascript:" not in cleaned.lower()
    assert "alert(1)" not in cleaned
    assert "Click me" in cleaned


def test_sanitize_html_strips_iframes_and_objects():
    malicious = '<iframe src="https://evil.com"></iframe><object data="bad.swf"></object><embed src="bad.pdf">'
    cleaned = sanitize_html_content(malicious)
    assert "<iframe" not in cleaned
    assert "<object" not in cleaned
    assert "<embed" not in cleaned


def test_sanitize_html_strips_forms_and_inputs():
    malicious = '<form action="https://phish.com" method="POST"><input type="password" name="pwd"><button>Submit</button></form>'
    cleaned = sanitize_html_content(malicious)
    assert "<form" not in cleaned
    assert "<input" not in cleaned
    assert "<button" not in cleaned


def test_html_card_injects_strict_csp():
    title = "Test Security Card"
    markdown_text = "## Safe Title\n\nThis is safe markdown."
    compiled_html = ArtifactCompiler.compile_html_card(title, markdown_text, sources=[])

    assert "<meta http-equiv=\"Content-Security-Policy\"" in compiled_html
    assert "default-src 'none'" in compiled_html
    assert "connect-src 'none'" in compiled_html
    assert "frame-src 'none'" in compiled_html
    assert "form-action 'none'" in compiled_html
    assert "<script>" not in compiled_html
