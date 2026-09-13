# Finding Schema

Every sub-skill returns a JSON array of finding objects. Each finding must
have these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Short human-readable title of the problem |
| `severity` | string | yes | One of: `critical`, `high`, `medium`, `low` |
| `category` | string | yes | `discoverability` or `engagement` |
| `sub_category` | string | no | Specific concern area |
| `evidence` | string | yes | Concrete evidence with numbers and specifics |
| `suggested_action` | object | yes | Action to fix the problem |
| `pages_affected` | array | no | URLs where this finding was detected |

## suggested_action object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary` | string | yes | What to change and how (specific, actionable) |
| `priority` | string | yes | `critical`, `high`, `medium`, or `low` |
| `effort` | string | no | `low`, `medium`, or `high` |

## Example

```json
{
  "title": "No sitemap.xml found",
  "severity": "medium",
  "category": "discoverability",
  "sub_category": "crawlability",
  "evidence": "Checked https://example.com/sitemap.xml (404) and https://example.com/sitemap_index.xml (404). No Sitemap directive in robots.txt.",
  "suggested_action": {
    "summary": "Create a sitemap.xml at the site root listing all public URLs. Reference it in robots.txt with a 'Sitemap: https://example.com/sitemap.xml' directive.",
    "priority": "medium",
    "effort": "low"
  },
  "pages_affected": ["https://example.com/"]
}
```
