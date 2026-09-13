#!/usr/bin/env python3
"""
check_render.py — Diagnostic script for crawl-render audit.

Fetches a URL, analyzes the raw HTML for client-side rendering gaps,
and prints a diagnostic summary that the skill can use to build findings.

Usage:
    python3 check_render.py <url> [--pages N]

Outputs JSON with:
  - status_code: HTTP response code
  - final_url: URL after redirects
  - text_length: chars of visible text in raw HTML
  - is_app_shell: whether the page appears to be a JS-only app shell
  - framework_hints: detected frontend framework markers
  - has_noscript_fallback: whether <noscript> has meaningful content
  - meta_robots: value of <meta name="robots"> tag
  - canonical: value of <link rel="canonical"> href
  - internal_links: list of internal URLs found
  - heading_tags: counts of h1, h2, h3
"""

import sys
import re
import json
import argparse
import urllib.request
import urllib.parse
from html.parser import HTMLParser

MAX_REDIRECTS = 5


class HTMLAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_length = 0
        self.in_script = False
        self.in_style = False
        self.in_noscript = False
        self.noscript_text = ""
        self.meta_robots = None
        self.canonical = None
        self.h1_count = 0
        self.h2_count = 0
        self.h3_count = 0
        self.internal_links = []
        self.framework_hints = []
        self.app_mount_empty = False
        self.has_next_data = False
        self._current_tag = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag

        if tag == "script":
            self.in_script = True
            script_src = attrs_dict.get("src", "")
            script_type = attrs_dict.get("type", "")
            if script_type == "application/ld+json":
                pass  # JSON-LD is fine
            elif "next" in script_src.lower():
                self.framework_hints.append("Next.js")

        if tag == "style":
            self.in_style = True

        if tag == "noscript":
            self.in_noscript = True

        if tag == "meta":
            name = attrs_dict.get("name", "").lower()
            if name == "robots":
                self.meta_robots = attrs_dict.get("content", "")

        if tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            if rel == "canonical":
                self.canonical = attrs_dict.get("href", "")

        if tag == "div":
            element_id = attrs_dict.get("id", "")
            if element_id in ("root", "app", "__next", "__nuxt"):
                self.framework_hints.append(
                    f"app-mount-point: #{element_id}"
                )
                self.app_mount_empty = True  # will be set False if children found

        if tag in ("h1", "h2", "h3"):
            if tag == "h1":
                self.h1_count += 1
            elif tag == "h2":
                self.h2_count += 1
            elif tag == "h3":
                self.h3_count += 1

        if tag == "a":
            href = attrs_dict.get("href", "")
            if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
                self.internal_links.append(href)

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        if tag == "style":
            self.in_style = False
        if tag == "noscript":
            self.in_noscript = False
        self._current_tag = None

    def handle_data(self, data):
        if self.in_script or self.in_style:
            return
        stripped = data.strip()
        if stripped:
            self.text_length += len(stripped)
            if self.in_noscript:
                self.noscript_text += stripped

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def fetch_url(url: str) -> tuple[int, str, str, dict]:
    """Fetch URL and return (status_code, final_url, body, headers)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BrandAIAuditBot/1.0 (audit; read-only)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, resp.url, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, e.url or url, body, dict(e.headers or {})
    except Exception as e:
        return 0, url, str(e), {}


def is_internal_link(link: str, base_domain: str) -> bool:
    """Check if a link is internal to the base domain."""
    if link.startswith("/"):
        return True
    parsed = urllib.parse.urlparse(link)
    if parsed.netloc:
        base = urllib.parse.urlparse(base_domain)
        return parsed.netloc == base.netloc or parsed.netloc.endswith(
            "." + base.netloc
        )
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Diagnostic for crawl-render audit"
    )
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument(
        "--pages", type=int, default=10,
        help="Max pages to crawl (default 10)"
    )
    args = parser.parse_args()

    if not args.url.startswith("http"):
        args.url = "https://" + args.url

    base_domain = args.url
    status, final_url, body, headers = fetch_url(args.url)

    analyzer = HTMLAnalyzer()
    analyzer.feed(body)

    # Check for Next.js data
    if "__NEXT_DATA__" in body:
        analyzer.has_next_data = True
        analyzer.framework_hints.append("Next.js (CSR)")

    # Check for common framework markers
    if "data-reactroot" in body or "reactroot" in body:
        analyzer.framework_hints.append("React")
    if "data-v-" in body:
        analyzer.framework_hints.append("Vue")
    if "ng-version" in body:
        analyzer.framework_hints.append("Angular")
    if "svelte" in body.lower():
        analyzer.framework_hints.append("Svelte")

    # Filter internal links
    base_parsed = urllib.parse.urlparse(args.url)
    base_netloc = base_parsed.netloc
    internal_links = [
        link for link in analyzer.internal_links
        if is_internal_link(link, base_netloc)
    ]
    internal_links = list(set(internal_links))[:args.pages]

    is_app_shell = (
        analyzer.text_length < 200
        and len(analyzer.framework_hints) > 0
    )

    result = {
        "status_code": status,
        "final_url": final_url,
        "text_length": analyzer.text_length,
        "is_app_shell": is_app_shell,
        "framework_hints": list(set(analyzer.framework_hints)),
        "has_noscript_fallback": len(analyzer.noscript_text) > 50,
        "noscript_text_length": len(analyzer.noscript_text),
        "meta_robots": analyzer.meta_robots,
        "canonical": analyzer.canonical,
        "heading_counts": {
            "h1": analyzer.h1_count,
            "h2": analyzer.h2_count,
            "h3": analyzer.h3_count,
        },
        "internal_links_count": len(internal_links),
        "internal_links": internal_links,
        "response_headers": {
            k: v for k, v in headers.items()
            if k.lower() in ("x-robots-tag", "content-type", "last-modified")
        },
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
