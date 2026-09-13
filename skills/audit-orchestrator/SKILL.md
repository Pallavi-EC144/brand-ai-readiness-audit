---
name: audit-orchestrator
description: >
  Entrypoint skill for the Brand AI-Readiness Audit marketplace. Receives a
  website URL, delegates to five focused sub-skills (crawl-render-audit,
  structured-data-audit, content-extractability-audit,
  freshness-corroboration-audit, engagement-audit), collects their findings,
  deduplicates, assigns finding IDs, computes summary counts, adds proactive
  recommendations, and emits a single structured audit report in JSON.
  Use when diagnosing why a brand is missing or misrepresented in AI
  assistants, or why visitors who arrive don't engage.
license: MIT
allowed-tools:
  - WebFetch
  - WebSearch
---

# Audit Orchestrator (Entrypoint)

## When to use

Invoke this skill when asked to audit a website for AI-discoverability and
on-site engagement problems. It is the single entrypoint for the
`brand-ai-readiness-audit` marketplace and is responsible for composing the
outputs of all other skills into one final report.

## Inputs

- **url** (required) — the root URL or domain to audit (e.g. `https://example.com`)
- **depth** (optional, default `1`) — how many internal pages to crawl beyond the root (0 = root only, 1 = root + linked pages)
- **max-pages** (optional, default `10`) — maximum number of pages to fetch

## Procedure

1. **Validate input.** Confirm `url` is a well-formed HTTP(S) URL. If a bare
   domain is given, prepend `https://`.

2. **Resolve sub-skills.** Load the five focused audit skills from the
   marketplace, in this order:

   | Order | Skill | Concern |
   |-------|-------|---------|
   | 1 | `crawl-render-audit` | Can crawlers reach and read the page? |
   | 2 | `structured-data-audit` | Is there valid structured data (schema.org / JSON-LD)? |
   | 3 | `content-extractability-audit` | Are key facts in extractable text or locked in non-text? |
   | 4 | `freshness-corroboration-audit` | Are facts fresh and corroborated across sources? |
   | 5 | `engagement-audit` | Does the page orient and retain visitors? |

3. **Execute each sub-skill** in order. Pass the validated URL, depth, and
   max-pages to each. Collect the findings array each returns.

4. **Deduplicate findings.** If two sub-skills report the same underlying
   issue (e.g. crawl-render finds "JS-rendered content" and
   content-extractability finds "facts locked in client-rendered DOM"),
   merge them into one finding, combining evidence strings.

5. **Assign finding IDs.** Sort all findings by severity (critical → high →
   medium → low), then assign sequential IDs: `F-001`, `F-002`, …

6. **Add proactive recommendations.** Review the combined findings for gaps
   where no defect was detected but a proactive improvement would strengthen
   discoverability or engagement. Add these as additional findings with
   severity `low` and an `"evidence"` note explaining the opportunity. See
   `references/proactive-checks.md` for the checklist.

7. **Compute summary.** Count total findings and per-severity counts.

8. **Assemble and emit the final report** in the schema defined in
   `references/report-schema.md`. Run `scripts/assemble_report.py` to
   validate the structure and format the JSON.

## Output

A single JSON object matching this minimum schema:

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": {
    "total_findings": 6,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 0
  },
  "findings": [
    {
      "id": "F-001",
      "title": "...",
      "severity": "high",
      "category": "discoverability | engagement",
      "sub_category": "structured-data | crawlability | ...",
      "evidence": "...",
      "suggested_action": {
        "summary": "...",
        "priority": "high",
        "effort": "low | medium | high"
      }
    }
  ]
}
```

Each finding must include: `id`, `title`, `severity`, `evidence`,
`suggested_action` (with `summary` and `priority`). The report must include
`site`, `audited_at`, and a `summary` with `total_findings` and per-severity
counts.

## Safety

- Read-only. No skill in this marketplace modifies a live website.
- Respect `robots.txt`. Do not crawl disallowed paths.
- Do not authenticate, submit forms, or perform any write actions.
- Do not make more than 30 HTTP requests per audit.
