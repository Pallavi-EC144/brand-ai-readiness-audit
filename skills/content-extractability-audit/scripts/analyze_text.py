#!/usr/bin/env python3
"""
analyze_text.py — Analyze page HTML for content extractability.

Fetches a URL, extracts visible text, detects non-text content containers,
checks heading structure, and assesses whether key facts are in plain text.

Usage:
    python3 analyze_text.py <url>

Outputs JSON with:
  - url: fetched URL
  - visible_text_length: chars of text after stripping script/style
  - visible_text_sample: first 500 chars of visible text
  - img_count: number of <img> tags
  - imgs_with_alt: number of <img> with alt text
  - imgs_textual_alt: images whose alt suggests text content
  - iframe_count: number of <iframe> embeds
  - canvas_count: number of <canvas> elements
  - video_count: number of <video> elements
  - pdf_links: list of PDF links found
  - svg_text_count: number of <text> elements inside <svg>
  - heading_structure: {h1, h2, h3, h4, h5, h6 counts}
  - title: <title> tag content
  - meta_description: <meta name="description"> content
  - has_h1: whether at least one <h1> exists
  - multiple_h1: whether more than one <h1> exists
  - noscript_content_length: text in <noscript> blocks
  - js_obfuscation_hints: detected JS text construction patterns
"""

import sys
import re
import json
import argparse
import urllib.request
from html.parser import HTMLParser


def fetch_html(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BrandAIAuditBot/1.0 (audit; read-only)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


class TextAnalyzer(HTMLParser):
    TEXTUAL_ALT_KEYWORDS = [
        "price", "pricing", "hours", "menu", "contact",
        "address", "phone", "email", "schedule", "table",
        "chart", "specifications", "specs", "rate", "fee",
        "directions", "location", "calendar", "form",
    ]

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script = False
        self.in_style = False
        self.in_svg = False
        self.svg_text_count = 0
        self.img_count = 0
        self.imgs_with_alt = 0
        self.imgs_textual_alt = 0
        self.iframe_count = 0
        self.canvas_count = 0
        self.video_count = 0
        self.pdf_links = []
        self.title = None
        self.meta_description = None
        self.headings = {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0}
        self.noscript_content = []
        self.in_noscript = False
        self.in_title = False
        self._title_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "script":
            self.in_script = True
        elif tag == "style":
            self.in_style = True
        elif tag == "svg":
            self.in_svg = True
        elif tag == "text" and self.in_svg:
            self.svg_text_count += 1
        elif tag == "img":
            self.img_count += 1
            alt = attrs_dict.get("alt", "")
            if alt:
                self.imgs_with_alt += 1
                alt_lower = alt.lower()
                if any(kw in alt_lower for kw in self.TEXTUAL_ALT_KEYWORDS):
                    self.imgs_textual_alt += 1
        elif tag == "iframe":
            self.iframe_count += 1
        elif tag == "canvas":
            self.canvas_count += 1
        elif tag == "video":
            self.video_count += 1
        elif tag == "a":
            href = attrs_dict.get("href", "")
            if href.lower().endswith(".pdf"):
                self.pdf_links.append(href)
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            if name == "description":
                self.meta_description = attrs_dict.get("content", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "noscript":
            self.in_noscript = True
        elif tag in self.headings:
            self.headings[tag] += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False
        elif tag == "svg":
            self.in_svg = False
        elif tag == "noscript":
            self.in_noscript = False
        elif tag == "title":
            self.in_title = False
            self.title = "".join(self._title_parts).strip()
            self._title_parts = []

    def handle_data(self, data):
        if self.in_script or self.in_style:
            return
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)
            if self.in_noscript:
                self.noscript_content.append(stripped)
            if self.in_title:
                self._title_parts.append(stripped)


def detect_js_obfuscation(html: str) -> list[str]:
    """Detect patterns where text is constructed via JS."""
    hints = []

    # Email obfuscation patterns
    if re.search(r'document\.write\s*\(', html, re.IGNORECASE):
        hints.append("document.write usage (content constructed at runtime)")
    if re.search(r'\.innerHTML\s*=', html, re.IGNORECASE):
        hints.append("innerHTML assignment (content injected via JS)")
    if re.search(r'atob\s*\(', html):
        hints.append("base64 decode (possible email/text obfuscation)")
    if re.search(r'String\.fromCharCode', html):
        hints.append("String.fromCharCode (character-level text construction)")

    # Email-specific patterns
    email_js = re.search(r'["\']([a-zA-Z0-9._%+-]+)\s*["\']\s*\+\s*["\']@', html)
    if email_js:
        hints.append("email address split across JS string concatenation")

    return hints


def main():
    parser = argparse.ArgumentParser(
        description="Analyze page content extractability"
    )
    parser.add_argument("url", help="URL to analyze")
    args = parser.parse_args()

    html = fetch_html(args.url)
    if not html:
        print(json.dumps({"error": "Failed to fetch URL", "url": args.url}, indent=2))
        sys.exit(1)

    analyzer = TextAnalyzer()
    analyzer.feed(html)

    visible_text = " ".join(analyzer.text_parts)
    noscript_text = " ".join(analyzer.noscript_content)

    js_hints = detect_js_obfuscation(html)

    result = {
        "url": args.url,
        "visible_text_length": len(visible_text),
        "visible_text_sample": visible_text[:500],
        "img_count": analyzer.img_count,
        "imgs_with_alt": analyzer.imgs_with_alt,
        "imgs_textual_alt": analyzer.imgs_textual_alt,
        "imgs_without_alt": analyzer.img_count - analyzer.imgs_with_alt,
        "iframe_count": analyzer.iframe_count,
        "canvas_count": analyzer.canvas_count,
        "video_count": analyzer.video_count,
        "pdf_links": analyzer.pdf_links,
        "pdf_links_count": len(analyzer.pdf_links),
        "svg_text_count": analyzer.svg_text_count,
        "heading_structure": analyzer.headings,
        "title": analyzer.title,
        "meta_description": analyzer.meta_description,
        "has_h1": analyzer.headings["h1"] > 0,
        "multiple_h1": analyzer.headings["h1"] > 1,
        "noscript_content_length": len(noscript_text),
        "js_obfuscation_hints": js_hints,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
