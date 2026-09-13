#!/usr/bin/env python3
"""
assemble_report.py — Validates and formats the final audit report JSON.

Usage:
    python3 assemble_report.py <findings-json-file> [--site example.com]

Reads a JSON file containing an array of finding objects (as produced by
the sub-skills), validates the required fields, assigns sequential IDs,
computes summary counts, and prints the complete report JSON to stdout.
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from collections import Counter

VALID_SEVERITIES = ["critical", "high", "medium", "low"]
SEVERITY_ORDER = {s: i for i, s in enumerate(VALID_SEVERITIES)}

REQUIRED_FINDING_FIELDS = ["title", "severity", "evidence", "suggested_action"]
REQUIRED_ACTION_FIELDS = ["summary", "priority"]


def validate_finding(finding: dict, index: int) -> list[str]:
    """Validate a single finding object. Returns list of error messages."""
    errors = []
    for field in REQUIRED_FINDING_FIELDS:
        if field not in finding:
            errors.append(f"Finding {index}: missing required field '{field}'")

    if "severity" in finding and finding["severity"] not in VALID_SEVERITIES:
        errors.append(
            f"Finding {index}: invalid severity '{finding['severity']}'. "
            f"Must be one of {VALID_SEVERITIES}"
        )

    action = finding.get("suggested_action", {})
    if isinstance(action, dict):
        for field in REQUIRED_ACTION_FIELDS:
            if field not in action:
                errors.append(
                    f"Finding {index}: suggested_action missing '{field}'"
                )
        if "priority" in action and action["priority"] not in VALID_SEVERITIES:
            errors.append(
                f"Finding {index}: invalid priority '{action['priority']}'"
            )
    else:
        errors.append(f"Finding {index}: suggested_action must be an object")

    return errors


def deduplicate(findings: list[dict]) -> list[dict]:
    """Merge findings with the same title (case-insensitive)."""
    seen: dict[str, dict] = {}
    for f in findings:
        key = f.get("title", "").lower().strip()
        if key in seen:
            existing = seen[key]
            existing["evidence"] = existing.get("evidence", "") + " | " + f.get("evidence", "")
            if "pages_affected" in f:
                existing_pages = set(existing.get("pages_affected", []))
                existing_pages.update(f["pages_affected"])
                existing["pages_affected"] = list(existing_pages)
        else:
            seen[key] = dict(f)
    return list(seen.values())


def assign_ids(findings: list[dict]) -> list[dict]:
    """Sort by severity and assign sequential IDs."""
    sorted_findings = sorted(
        findings,
        key=lambda f: SEVERITY_ORDER.get(f.get("severity", "low"), 3)
    )
    for i, f in enumerate(sorted_findings, 1):
        f["id"] = f"F-{i:03d}"
    return sorted_findings


def compute_summary(findings: list[dict]) -> dict:
    """Compute summary counts."""
    counts = Counter(f.get("severity", "low") for f in findings)
    return {
        "total_findings": len(findings),
        "critical": counts.get("critical", 0),
        "high": counts.get("high", 0),
        "medium": counts.get("medium", 0),
        "low": counts.get("low", 0),
    }


def assemble(findings: list[dict], site: str) -> dict:
    """Assemble the final report."""
    findings = deduplicate(findings)
    findings = assign_ids(findings)
    summary = compute_summary(findings)

    return {
        "site": site,
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Assemble and validate the final audit report"
    )
    parser.add_argument(
        "findings_file",
        help="Path to JSON file containing an array of finding objects"
    )
    parser.add_argument(
        "--site",
        default="unknown",
        help="Site domain/URL being audited"
    )
    args = parser.parse_args()

    with open(args.findings_file, "r") as f:
        findings = json.load(f)

    if not isinstance(findings, list):
        print("Error: findings file must contain a JSON array", file=sys.stderr)
        sys.exit(1)

    all_errors = []
    for i, finding in enumerate(findings):
        all_errors.extend(validate_finding(finding, i))

    if all_errors:
        for e in all_errors:
            print(f"Validation error: {e}", file=sys.stderr)
        sys.exit(1)

    report = assemble(findings, args.site)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
