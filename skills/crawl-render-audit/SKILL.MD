---
name: crawl-render-audit
description: >
  Audits whether automated crawlers and AI assistants can reach and read a
  website. Checks robots.txt, sitemap.xml, HTTP status, meta robots
  directives, and whether critical content is server-rendered or locked
  behind client-side JavaScript execution. Detects the three-step
  crawlability failure: crawler blocked, crawler can't read, or crawler
  can't extract facts. Use as part of the brand-ai-readiness-audit
  marketplace.
license: MIT
allowed-tools:
  - WebFetch
  - WebSearch
---

# Crawl-Render Audit

## When to use

Invoke this skill to determine whether a page is reachable and readable by
automated systems (search-engine crawlers, AI-assistant fetchers). This is
the first step in the audit pipeline — if a page fails here, downstream
checks are affected.

## Inputs

- **url** (required) — root URL to audit
- **depth** (optional, default `1`) — pages to crawl beyond root
- **max-pages** (optional, default `10`) — max pages to fetch

## Procedure

1. **Fetch `robots.txt`** at `{url}/robots.txt`.
   - If present, parse Disallow rules. Record any broad blocks
     (`Disallow: /` or paths covering key sections).
   - If absent, note as a low-severity finding (no crawl guidance).
   - Check for `Sitemap:` directives and record the sitemap URLs.

2. **Fetch `sitemap.xml`** (if declared in robots.txt or found at
   `{url}/sitemap.xml`, `{url}/sitemap_index.xml`).
   - If present, count URLs listed. A sitemap with 0 URLs or only the
     homepage is a weak signal.
   - If absent, note as a medium-severity finding — crawlers must discover
     pages via links only.

3. **Fetch the root page** and record:
   - HTTP status code (anything other than 200 is a finding).
   - Final URL after redirects (redirect chains > 2 hops are a finding).
   - Response headers: `X-Robots-Tag`, `Content-Type`, `Content-Length`.
   - Whether the response body contains meaningful text content (> 200
     chars of visible text).

4. **Detect client-side rendering gaps.** Compare the server-delivered HTML
   with what a user would see:
   - Check if the page is a known CSR framework (React, Vue, Angular,
     Next.js without SSR, etc.) by looking for `#__NEXT_DATA__`,
     `<div id="root">` with no children, or framework-specific markers.
   - Check for `<noscript>` tags with messages like "enable JavaScript" —
     this indicates content requires JS execution.
   - Check if key content elements (`<h1>`, `<main>`, `<article>`) are
     empty or absent in the raw HTML but expected on the page.
   - Count the visible text length in the raw HTML. If it's < 200 chars
     and the page appears to be an app shell, flag as a critical finding.

5. **Check meta robots directives.** Look for `<meta name="robots">` tags:
   - `noindex` → critical: page won't be indexed.
   - `nofollow` → high: link equity not passed.
   - `none` → critical: equivalent to noindex,nofollow.

6. **Check canonical tags.** Look for `<link rel="canonical">`:
   - If canonical points to a different URL, the page may not be the
     authoritative version — medium finding.
   - If missing, note as low — not required but recommended.

7. **Crawl linked pages** (up to max-pages). For each internal link found
   on the root page:
   - Fetch and record HTTP status.
   - If > 20% of internal links return non-200, flag as high finding
     (broken internal linking).

8. **Emit findings.** Return an array of finding objects matching the
   schema in `references/finding-schema.md`. Each finding must include:
   `title`, `severity`, `category` (always `"discoverability"`),
   `sub_category`, `evidence`, and `suggested_action`.

## Output

A JSON array of findings. See `references/finding-schema.md` for the exact
shape. Run `scripts/check_render.py <url>` to automate steps 3–4 and
generate a diagnostic summary.

## Severity guidelines

| Condition | Severity |
|-----------|----------|
| Root page returns non-200 or redirects to a different domain | critical |
| `noindex` / `none` meta robots tag | critical |
| robots.txt blocks all crawlers (`Disallow: /`) | critical |
| Page is JS-only app shell with < 200 chars text in raw HTML | critical |
| > 20% internal links broken | high |
| `nofollow` meta tag | high |
| No sitemap.xml | medium |
| No canonical tag | low |
| No robots.txt | low |

## Safety

- Read-only HTTP GET only.
- Respect all `robots.txt` Disallow rules — do not fetch disallowed paths.
- Limit to max-pages HTTP requests.
