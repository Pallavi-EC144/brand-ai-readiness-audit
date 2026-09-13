#!/usr/bin/env python3
"""
check_freshness.py — Detect freshness signals in page HTML.

Scans HTML for date/time signals, copyright years, stale content indicators,
and structured data dates. Prints a diagnostic summary.

Usage:
    python3 check_freshness.py <url>

Outputs JSON with:
  - url: fetched URL
  - freshness_signals: list of detected signals with type and value
  - has_any_signal: whether any freshness signal was found
  - copyright_year: latest copyright year found in footer text
  - last_modified_header: HTTP Last-Modified header value
  - jsonld_dates: datePublished/dateModified from JSON-LD
  - meta_dates: article:modified_time / article:published_time
  - time_tags: <time datetime> values found
  - stale_indicators: detected stale content patterns
"""

import sys
import re
import json
import argparse
import urllib.request
from html.parser import HTMLParser


def fetch_url(url: str) -> tuple[str, str, dict]:
    """Fetch URL, return (html, final_url, headers)."""
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BrandAIAuditBot/1.0 (audit; read-only)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace"), resp.url, dict(resp.headers)
    except Exception as e:
        return "", url, {}


class FreshnessAnalyzer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.time_tags = []
        self.meta_dates = {}
        self.jsonld_dates = {}
        self.copyright_years = set()
        self.visible_dates = []
        self.in_script = False
        self.in_style = False
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "script":
            self.in_script = True
            script_type = attrs_dict.get("type", "")
            if script_type == "application/ld+json":
                pass  # handled in data
        elif tag == "style":
            self.in_style = True
        elif tag == "time":
            dt = attrs_dict.get("datetime", "")
            if dt:
                self.time_tags.append(dt)
        elif tag == "meta":
            prop = attrs_dict.get("property", attrs_dict.get("name", "")).lower()
            content = attrs_dict.get("content", "")
            if "modified" in prop and content:
                self.meta_dates["modified"] = content
            elif "published" in prop and content:
                self.meta_dates["published"] = content

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_script or self.in_style:
            return
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)

        # Detect copyright years
        cr_match = re.search(r'[©\(c\)]\s*(\d{4})', stripped, re.IGNORECASE)
        if cr_match:
            self.copyright_years.add(int(cr_match.group(1)))

        # Detect "Last updated" / "Updated on" patterns
        date_patterns = [
            r'(?:last\s+updated|updated(?:\s+on)?|modified(?:\s+on)?)\s*:?\s*(\d{4}[-/]\d{2}[-/]\d{2}|\w+\s+\d{1,2},?\s+\d{4})',
            r'(?:published(?:\s+on)?)\s*:?\s*(\d{4}[-/]\d{2}[-/]\d{2}|\w+\s+\d{1,2},?\s+\d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, stripped, re.IGNORECASE)
            if match:
                self.visible_dates.append(match.group(0))


def extract_jsonld_dates(html: str) -> dict:
    """Extract datePublished and dateModified from JSON-LD blocks."""
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    dates = {}

    for raw in matches:
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue

        nodes = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and "@graph" in data:
            nodes = data["@graph"] if isinstance(data["@graph"], list) else [data["@graph"]]

        for node in nodes:
            if not isinstance(node, dict):
                continue
            for field in ("datePublished", "dateModified", "startDate", "endDate"):
                if field in node and field not in dates:
                    dates[field] = str(node[field])

    return dates


def detect_stale_indicators(html: str, text: str) -> list[str]:
    """Detect patterns suggesting stale content."""
    indicators = []
    current_year = 2026
    two_years_ago = current_year - 2

    # Check copyright years
    cr_matches = re.findall(r'[©\(c\)]\s*(\d{4})', text, re.IGNORECASE)
    for year_str in cr_matches:
        year = int(year_str)
        if year < two_years_ago:
            indicators.append(f"Copyright year {year} is more than 2 years old")

    # Check for past event references in present tense
    # (hard to detect reliably, but check for year references in event contexts)
    past_years = re.findall(r'\b(20[0-2]\d)\b', text)
    for year_str in past_years:
        year = int(year_str)
        if year < two_years_ago and "join us" in text.lower():
            indicators.append(f"Possible stale event reference: year {year} mentioned with present-tense invitation language")

    return indicators


def main():
    parser = argparse.ArgumentParser(
        description="Detect freshness signals in a page"
    )
    parser.add_argument("url", help="URL to analyze")
    args = parser.parse_args()

    html, final_url, headers = fetch_url(args.url)
    if not html:
        print(json.dumps({"error": "Failed to fetch URL", "url": args.url}, indent=2))
        sys.exit(1)

    analyzer = FreshnessAnalyzer()
    analyzer.feed(html)

    visible_text = " ".join(analyzer.text_parts)
    jsonld_dates = extract_jsonld_dates(html)
    stale_indicators = detect_stale_indicators(html, visible_text)

    freshness_signals = []

    if analyzer.time_tags:
        freshness_signals.append({"type": "time_tag", "values": analyzer.time_tags})
    if analyzer.meta_dates:
        freshness_signals.append({"type": "meta_date", "values": analyzer.meta_dates})
    if analyzer.visible_dates:
        freshness_signals.append({"type": "visible_date_text", "values": analyzer.visible_dates})
    if analyzer.copyright_years:
        freshness_signals.append({
            "type": "copyright_year",
            "values": sorted(analyzer.copyright_years, reverse=True)
        })
    if jsonld_dates:
        freshness_signals.append({"type": "jsonld_date", "values": jsonld_dates})

    last_modified = headers.get("Last-Modified", headers.get("last-modified", ""))
    if last_modified:
        freshness_signals.append({"type": "http_header", "value": last_modified})

    result = {
        "url": final_url,
        "has_any_signal": len(freshness_signals) > 0,
        "freshness_signals": freshness_signals,
        "copyright_years": sorted(analyzer.copyright_years, reverse=True) if analyzer.copyright_years else None,
        "last_modified_header": last_modified or None,
        "jsonld_dates": jsonld_dates if jsonld_dates else None,
        "meta_dates": analyzer.meta_dates if analyzer.meta_dates else None,
        "time_tags": analyzer.time_tags if analyzer.time_tags else None,
        "visible_date_references": analyzer.visible_dates if analyzer.visible_dates else None,
        "stale_indicators": stale_indicators if stale_indicators else [],
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
