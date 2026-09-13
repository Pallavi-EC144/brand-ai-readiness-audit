# Brand AI-Readiness Audit Marketplace

A portable Agent Skill Marketplace for auditing websites for two concerns:

1. **AI discoverability** — whether important brand facts are reachable, extractable, structured, identifiable, and reasonably fresh.
2. **On-site engagement** — whether a visitor can understand the page, navigate it, and find a clear next action.

The marketplace is recommend-only and read-only. It does not log in, submit forms, modify websites, or require proprietary APIs.

## Marketplace structure

```text
brand-ai-readiness-audit/
├── marketplace.json                 # marketplace manifest; one entrypoint
├── README.md
├── index.html                       # optional Vercel demo UI
├── api/
│   └── audit.py                     # optional Vercel HTTP adapter
├── runtime/
│   └── audit_engine.py              # portable deterministic audit runtime
└── skills/
    ├── audit-orchestrator/SKILL.md
    ├── crawl-render-audit/SKILL.MD
    ├── structured-data-audit/SKILL.md
    ├── content-extractability-audit/SKILL.md
    ├── freshness-corroboration-audit/SKILL.md
    └── engagement-audit/SKILL.md
```

## Agent Skill Marketplace

`marketplace.json` lists six skills and designates only `audit-orchestrator` as the entrypoint. The skill files are the agent-facing instructions; the `runtime/` implementation provides a deterministic read-only execution path for the included demo.

The intended composition is:

```text
URL
 ↓
audit-orchestrator
 ↓
┌───────────────────────┐
│ crawl / render        │
│ structured data       │
│ content extractability│
│ freshness / identity  │
│ engagement            │
└───────────────────────┘
 ↓
dedupe + severity + priority
 ↓
structured JSON report
```

## Vercel demo

The Vercel layer is deliberately thin and is **not required by the marketplace format**.

- `api/audit.py` exposes `GET /api/audit?url=https://example.com`.
- `runtime/audit_engine.py` performs the read-only audit using only the Python standard library.
- `index.html` provides a small browser UI for demonstrating the audit.
- `vercel.json` caps the audit function at 240 seconds so a normal run stays below the hackathon's five-minute target.
- There are no API keys, databases, Bolt SDKs, or vendor-specific audit dependencies.

Example:

```text
https://YOUR-PROJECT.vercel.app/api/audit?url=https://example.com
```

The endpoint returns the required report shape:

```json
{
  "site": "example.com",
  "audited_at": "2026-09-20T14:32:00Z",
  "summary": {
    "total_findings": 2,
    "critical": 0,
    "high": 1,
    "medium": 1,
    "low": 0
  },
  "findings": [
    {
      "id": "F-001",
      "title": "...",
      "severity": "high",
      "category": "discoverability",
      "sub_category": "...",
      "evidence": "...",
      "suggested_action": {
        "summary": "...",
        "priority": "high",
        "effort": "medium"
      }
    }
  ]
}
```

## Running locally

The audit engine has no third-party Python dependency:

```bash
python -m py_compile runtime/audit_engine.py api/audit.py
```

For a local Vercel-style environment, install the Vercel CLI and run:

```bash
vercel dev
```

Then open:

```text
http://localhost:3000/
```

or call:

```text
http://localhost:3000/api/audit?url=https://example.com
```

## Safety and limitations

- Read-only HTTP GET requests only.
- Respects `robots.txt` when it is reachable.
- Same-domain crawl only.
- Conservative crawl limit; the API accepts at most 12 pages.
- No authentication, form submission, destructive requests, or site writes.
- Rejects obvious localhost/private/link-local targets to reduce SSRF risk.
- Static HTML analysis cannot fully observe content that appears only after client-side JavaScript execution. Such cases are reported conservatively rather than pretending that a full browser rendered the site.
- External corroboration is intentionally not fabricated by the deterministic runtime. The freshness/entity skill describes how an agent can use web search when the marketplace is executed in an agent environment.

## Submission note

For the hackathon submission, the marketplace remains portable: `marketplace.json` and `skills/` are the core deliverable. The Vercel files are an optional live demonstration layer and do not require Vercel for marketplace execution.
