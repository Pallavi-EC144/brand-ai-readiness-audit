# Brand AI-Readiness Audit Marketplace

A multi-skill agent marketplace that audits any website for two categories
of problems:

1. **AI discoverability** — why a brand isn't found or cited by AI assistants
2. **On-site engagement** — why visitors who arrive don't stay

Given a website URL, the marketplace produces a structured audit report
with evidence-backed findings and prioritized, actionable suggested actions.

## Quick start

Point the entrypoint skill at a URL:

> "Audit https://example.com for AI discoverability and engagement issues."

The marketplace does the rest — fetching pages, running checks, and emitting
a structured JSON report.

## Architecture

```
brand-ai-readiness-audit/
├── marketplace.json              ← manifest (lists skills, marks entrypoint)
├── README.md                     ← this file
└── skills/
    ├── audit-orchestrator/       ← ENTRYPOINT: composes all sub-skills
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── assemble_report.py    ← validates + formats the final report
    │   └── references/
    │       ├── report-schema.md      ← the output schema
    │       └── proactive-checks.md   ← beyond-defect recommendations
    ├── crawl-render-audit/       ← Can crawlers reach and read the page?
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── check_render.py       ← HTTP + render-gap diagnostics
    │   └── references/
    │       └── finding-schema.md
    ├── structured-data-audit/    ← Is there valid schema.org / JSON-LD?
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── extract_jsonld.py     ← JSON-LD extraction + validation
    │   └── references/
    │       ├── finding-schema.md
    │       └── schema-org-types.md   ← type validation rules
    ├── content-extractability-audit/  ← Are facts in plain text or locked?
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── analyze_text.py       ← text extraction + non-text detection
    │   └── references/
    │       └── finding-schema.md
    ├── freshness-corroboration-audit/  ← Are facts fresh & corroborated?
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   └── check_freshness.py    ← date signal + staleness detection
    │   └── references/
    │       └── finding-schema.md
    └── engagement-audit/         ← Does the page orient and retain visitors?
        ├── SKILL.md
        ├── scripts/
        │   └── check_engagement.py   ← UX/engagement signal detection
        └── references/
            └── finding-schema.md
```

## Skill descriptions

### audit-orchestrator (Entrypoint)
Receives the audit request, delegates to all five sub-skills in order,
collects their findings, deduplicates overlapping issues, assigns finding
IDs sorted by severity, adds proactive recommendations, and assembles the
final JSON report. Uses `scripts/assemble_report.py` to validate the
report structure.

### crawl-render-audit
Checks the first barrier to AI discoverability: can automated systems
reach and read the page? Examines robots.txt, sitemap.xml, HTTP status,
redirect chains, meta robots directives, canonical tags, and — critically
— whether key content is in the server-delivered HTML or locked behind
client-side JavaScript execution (the "app shell" problem). Uses
`scripts/check_render.py` for automated diagnostics.

### structured-data-audit
Checks whether the page's key facts are encoded in machine-readable
structured data (schema.org JSON-LD, Microdata, RDFa). Validates the
presence, correctness, and coverage of Organization, Product, Service,
Event, Article, FAQPage, and other types. Checks for entity
disambiguation signals (`sameAs`, `@id`). Uses
`scripts/extract_jsonld.py` for extraction and validation.

### content-extractability-audit
Checks whether facts visible to humans are also available to machines.
Detects text locked in images, iframe widgets, canvas, video without
transcripts, PDFs that should be HTML, and JS-obfuscated contact info.
Also checks heading structure, page title, meta description, and whether
key facts are stated in plain declarative text. Uses
`scripts/analyze_text.py` for automated detection.

### freshness-corroboration-audit
Checks two trust factors: (A) freshness — are facts current, with
detectable last-updated signals, or stale and potentially misleading?
and (B) corroboration — do independent external sources agree with the
brand's claims? Detects entity ambiguity (multiple things sharing a name
without disambiguation). Uses `scripts/check_freshness.py` for date signal
detection and WebSearch for corroboration research.

### engagement-audit
Checks on-site engagement factors: first-impression orientation (clear
value proposition in the hero), navigation clarity, call-to-action
presence, mobile responsiveness, trust signals (HTTPS, reviews,
privacy policy), and performance indicators (render-blocking scripts,
image dimensions). Uses `scripts/check_engagement.py` for automated
detection.

## How the entrypoint composes the sub-skills

1. **Input validation** — the orchestrator normalizes the URL and
   validates parameters.

2. **Sequential delegation** — each sub-skill is invoked in order:
   crawl-render → structured-data → content-extractability →
   freshness-corroboration → engagement. Each receives the same URL and
   parameters and returns a JSON array of findings.

3. **Deduplication** — when two sub-skills surface the same underlying
   issue (e.g. crawl-render detects "JS app shell" and
   content-extractability detects "facts in client-rendered DOM"), the
   orchestrator merges them into one finding, combining evidence.

4. **ID assignment** — findings are sorted by severity (critical first)
   and assigned sequential IDs: F-001, F-002, ...

5. **Proactive recommendations** — the orchestrator reviews the combined
   findings for gaps where no defect was found but a proactive
   improvement would help. It checks the proactive-checks.md reference
   for a list of opportunities (FAQ page, Open Graph tags, Wikidata
   entry, etc.) and adds them as low-severity findings.

6. **Report assembly** — `scripts/assemble_report.py` validates the
   finding structure, computes summary counts, and emits the final JSON
   report.

## Output schema

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": {
    "total_findings": 6,
    "critical": 1,
    "high": 2,
    "medium": 2,
    "low": 1
  },
  "findings": [
    {
      "id": "F-001",
      "title": "...",
      "severity": "high",
      "category": "discoverability",
      "sub_category": "structured-data",
      "evidence": "...",
      "suggested_action": {
        "summary": "...",
        "priority": "high",
        "effort": "medium"
      },
      "pages_affected": ["https://example.com/"]
    }
  ]
}
```

## Design principles

- **Recommend-only.** No skill modifies a live website. Everything is
  read-only in a sandbox.
- **Respect robots.txt.** No crawling of disallowed paths.
- **No authentication.** No skill logs in, submits forms, or accesses
  protected areas.
- **Rate-limited.** Maximum 30 HTTP requests and 5 web searches per audit.
- **Portable.** Each skill declares its tool needs (WebFetch, WebSearch).
  The marketplace is self-contained — no external service needed.
- **Progressive disclosure.** SKILL.md files are lean; detailed checklists
  are in `references/` and executable checks are in `scripts/`.
- **Separation of concerns.** Each sub-skill handles one audit concern.
  The orchestrator composes them; it doesn't duplicate their checks.

## Safety & guardrails

- Read-only HTTP GET and web search only.
- No destructive, authenticated, or site-altering actions.
- Audit runtime: < 5 minutes for a typical website.
- Submission size: < 50 MB (no pre-trained model weights).
- Each skill is agentskills.io compliant (SKILL.md with YAML frontmatter).
- The marketplace manifest (`marketplace.json`) is self-contained with
  exactly one designated entrypoint.
