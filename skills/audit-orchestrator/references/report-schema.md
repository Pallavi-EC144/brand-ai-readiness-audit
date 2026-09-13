# Report Schema

The entrypoint skill emits a single JSON object with this shape.

## Required top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `site` | string | The domain or URL audited (e.g. `example.com`) |
| `audited_at` | string | ISO 8601 timestamp of when the audit was performed |
| `summary` | object | Counts of findings by severity |
| `findings` | array | List of finding objects |

## Summary object

| Field | Type | Description |
|-------|------|-------------|
| `total_findings` | integer | Total number of findings |
| `critical` | integer | Count of critical findings |
| `high` | integer | Count of high findings |
| `medium` | integer | Count of medium findings |
| `low` | integer | Count of low findings |

## Finding object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Sequential ID: `F-001`, `F-002`, ... |
| `title` | string | yes | Short human-readable title of the problem |
| `severity` | string | yes | One of: `critical`, `high`, `medium`, `low` |
| `category` | string | yes | `discoverability` or `engagement` |
| `sub_category` | string | no | Specific concern area (e.g. `structured-data`, `crawlability`) |
| `evidence` | string | yes | Concrete evidence: what was checked, what was found, with numbers |
| `suggested_action` | object | yes | What to do about it |
| `pages_affected` | array | no | List of page URLs where this finding was detected |

## Suggested action object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary` | string | yes | What to change and how (specific, actionable) |
| `priority` | string | yes | `critical`, `high`, `medium`, or `low` (usually matches severity) |
| `effort` | string | no | `low`, `medium`, or `high` — implementation effort estimate |

## Example

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
      "title": "Root page is a JavaScript app shell with no server-rendered text",
      "severity": "critical",
      "category": "discoverability",
      "sub_category": "crawlability",
      "evidence": "Fetched https://example.com/ — HTTP 200 but raw HTML body contains only 47 chars of text ('Loading...'). The page uses client-side rendering (Vue.js) with a <div id=\"app\"> mount point. No <noscript> fallback content found.",
      "suggested_action": {
        "summary": "Implement server-side rendering (SSR) or static pre-rendering so that the full page content is present in the initial HTML response. If using Vue, configure SSR with Nuxt.js or use a pre-rendering tool. At minimum, add a <noscript> block with key brand facts in plain text.",
        "priority": "critical",
        "effort": "high"
      }
    }
  ]
}
```
