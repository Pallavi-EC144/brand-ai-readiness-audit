#!/usr/bin/env python3
"""
extract_jsonld.py — Extract and validate JSON-LD blocks from a page.

Fetches a URL, finds all <script type="application/ld+json"> blocks,
parses and validates them, and prints a diagnostic summary.

Usage:
    python3 extract_jsonld.py <url>

Outputs JSON with:
  - url: the fetched URL
  - jsonld_blocks: count of JSON-LD blocks found
  - types: list of @type values found
  - valid: whether each block parsed successfully
  - details: per-block analysis (type, key properties present, errors)
  - has_organization: whether Organization/LocalBusiness exists
  - has_sameas: whether sameAs is present and how many links
  - has_id: whether @id is present
"""

import sys
import json
import re
import argparse
import urllib.request


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
    except Exception as e:
        return ""


def extract_jsonld_blocks(html: str) -> list[str]:
    """Extract raw JSON strings from <script type='application/ld+json'> tags."""
    pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
    return [m.strip() for m in matches]


def parse_jsonld(raw: str) -> dict | list | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        return {"_parse_error": str(e)}


def extract_type(node: dict) -> str | list:
    t = node.get("@type", "unknown")
    if isinstance(t, list):
        return t
    return str(t)


def check_key_props(node: dict, type_name: str) -> dict:
    """Check for key properties based on type."""
    checks = {}

    if type_name in ("Organization", "LocalBusiness", "NGO", "Corporation",
                      "EducationalOrganization", "GovernmentOrganization"):
        checks["name"] = "name" in node
        checks["url"] = "url" in node
        checks["logo"] = "logo" in node
        checks["sameAs"] = "sameAs" in node
        checks["description"] = "description" in node
        checks["address"] = "address" in node
        checks["telephone"] = "telephone" in node
        checks["email"] = "email" in node
        checks["@id"] = "@id" in node
        if "sameAs" in node:
            sameas = node["sameAs"]
            if isinstance(sameas, list):
                checks["sameAs_count"] = len(sameas)
            else:
                checks["sameAs_count"] = 1

    elif type_name == "Product":
        checks["name"] = "name" in node
        checks["description"] = "description" in node
        checks["image"] = "image" in node
        checks["brand"] = "brand" in node
        checks["offers"] = "offers" in node
        checks["aggregateRating"] = "aggregateRating" in node
        checks["sku"] = "sku" in node
        if "offers" in node:
            offers = node["offers"]
            if isinstance(offers, dict):
                checks["offers_has_price"] = "price" in offers
                checks["offers_has_currency"] = "priceCurrency" in offers
            elif isinstance(offers, list) and offers:
                checks["offers_has_price"] = "price" in offers[0]
                checks["offers_has_currency"] = "priceCurrency" in offers[0]

    elif type_name == "Article":
        checks["headline"] = "headline" in node
        checks["datePublished"] = "datePublished" in node
        checks["dateModified"] = "dateModified" in node
        checks["author"] = "author" in node
        checks["image"] = "image" in node
        checks["publisher"] = "publisher" in node

    elif type_name == "Event":
        checks["name"] = "name" in node
        checks["startDate"] = "startDate" in node
        checks["location"] = "location" in node
        checks["endDate"] = "endDate" in node
        checks["eventStatus"] = "eventStatus" in node

    elif type_name == "FAQPage":
        checks["mainEntity"] = "mainEntity" in node
        if "mainEntity" in node:
            me = node["mainEntity"]
            if isinstance(me, list):
                checks["question_count"] = len(me)

    elif type_name == "BreadcrumbList":
        checks["itemListElement"] = "itemListElement" in node
        if "itemListElement" in node:
            il = node["itemListElement"]
            if isinstance(il, list):
                checks["breadcrumb_count"] = len(il)

    return checks


def analyze_node(node: dict) -> dict:
    """Analyze a single JSON-LD node."""
    if "_parse_error" in node:
        return {"valid": False, "error": node["_parse_error"]}

    type_name = extract_type(node)
    types = type_name if isinstance(type_name, list) else [type_name]

    results = []
    for t in types:
        checks = check_key_props(node, t)
        results.append({"type": t, "properties": checks})

    return {
        "valid": True,
        "types": types,
        "has_@id": "@id" in node,
        "checks": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract and validate JSON-LD from a URL"
    )
    parser.add_argument("url", help="URL to analyze")
    args = parser.parse_args()

    html = fetch_html(args.url)
    if not html:
        print(json.dumps({"error": "Failed to fetch URL", "url": args.url}, indent=2))
        sys.exit(1)

    blocks = extract_jsonld_blocks(html)
    details = []
    all_types = []
    has_organization = False
    has_sameas = False
    sameas_count = 0
    has_id = False

    for raw in blocks:
        parsed = parse_jsonld(raw)
        if parsed is None:
            continue

        # Handle @graph arrays
        nodes = parsed if isinstance(parsed, list) else [parsed]
        if isinstance(parsed, dict) and "@graph" in parsed:
            nodes = parsed["@graph"] if isinstance(parsed["@graph"], list) else [parsed["@graph"]]

        for node in nodes:
            if not isinstance(node, dict):
                continue
            analysis = analyze_node(node)
            details.append(analysis)

            for t in analysis.get("types", []):
                all_types.append(t)
                if t in ("Organization", "LocalBusiness", "Corporation"):
                    has_organization = True

            if "sameAs" in node:
                has_sameas = True
                sameas = node["sameAs"]
                sameas_count = len(sameas) if isinstance(sameas, list) else 1

            if "@id" in node:
                has_id = True

    result = {
        "url": args.url,
        "jsonld_blocks": len(blocks),
        "types_found": list(set(all_types)),
        "has_organization": has_organization,
        "has_sameAs": has_sameas,
        "sameAs_count": sameas_count,
        "has_@id": has_id,
        "details": details,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
