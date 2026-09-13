---
name: freshness-corroboration-audit
description: >
  Audits whether the facts on a website are fresh (not stale) and
  corroborated by independent external sources. Detects outdated content,
  missing last-updated signals, facts that exist only on the site with no
  external agreement, and entity ambiguity (multiple things sharing a
  name without disambiguation). These factors cause AI assistants to
  distrust, ignore, or misrepresent a brand. Use as part of the
  brand-ai-readiness-audit marketplace.
license: MIT
allowed-tools:
  - WebFetch
  - WebSearch
---

# Freshness & Corroboration Audit

## When to use

Invoke this skill after the crawl-render and structured-data audits. This
skill checks whether the brand's facts are current and whether they are
repeated consistently across the wider web — two factors that strongly
influence whether AI assistants trust and repeat them.

## Inputs

- **url** (required) — root URL to audit
- **depth** (optional, default `1`) — pages to crawl beyond root
- **max-pages** (optional, default `10`) — max pages to fetch

## Procedure

### Part A — Freshness

1. **Fetch the root page HTML.** Look for freshness signals:

   | Signal | Where to look | Interpretation |
   |--------|--------------|----------------|
   | Visible date | Text like "Last updated: 2024-01-15" | Explicit freshness signal |
   | `<time>` tags | `<time datetime="...">` elements | Machine-readable date |
   | JSON-LD `datePublished` / `dateModified` | In Article/Event JSON-LD | Machine-readable freshness |
   | HTTP `Last-Modified` header | Response header | Server-level freshness |
   | `<meta property="article:modified_time">` | In `<head>` | Open Graph freshness signal |
   | Copyright year in footer | Text like "© 2023" | Stale if old, but weak signal |

   If no freshness signal is found on the root page, flag as **medium**
   (machines can't determine content age).

2. **Check for stale content indicators.**
   - Copyright year in footer > 2 years old → medium.
   - "Last updated" date > 2 years old on a page that describes current
     products/services → high.
   - References to past events using present tense ("Join us at
     [event]" for an event that already happened) → high.
   - Broken date-based URLs (e.g. `/blog/2021/...`) linked prominently
     from the root → low.
   - Pricing that appears outdated (e.g. "Starting at $9.99" with no
     date context, and competitor/current prices suggest it's stale) →
     low (needs corroboration; can't confirm purely from the page).

3. **Check blog/news section** (if linked from root):
   - If the most recent post is > 12 months old → medium (site appears
     abandoned).
   - If no blog/news section exists, this is not a finding (not all sites
     need a blog).

4. **Check for stale structured data.**
   - `Event` JSON-LD with `endDate` in the past and no `eventStatus` of
     `EventCancelled` → high (misleading: event listed as upcoming but
     already passed).
   - `Article` JSON-LD with `dateModified` > 2 years ago on a page about
     current products → medium.

### Part B — Corroboration

5. **Extract key brand facts** from the page:
   - Brand name
   - Type of business / what they do
   - Location(s)
   - Founding year
   - Key people (founders, executives)
   - Notable products/services

6. **Search the web for the brand name** (using WebSearch). For each
   result:
   - Is the brand's own website the first result? If not, flag as medium
     (brand's own site is not the authoritative source for its name).
   - Are there independent sources mentioning the brand (directories,
     news articles, Wikipedia, industry listings)? Count them.
   - Do the independent sources agree with the site's own claims
     (same location, same founding year, same business type)?

7. **Assess corroboration level:**
   - 0 independent sources → **high** (facts exist only on one source;
     fragile for AI trust).
   - 1-2 independent sources → medium.
   - 3+ independent sources → no finding (well-corroborated).

8. **Check entity ambiguity.** Search for the brand name alone. If
   multiple distinct entities share the name:
   - Is there a Wikipedia disambiguation page? → medium (confusable
     identity).
   - Does the brand have a unique identifier (Google Knowledge Graph ID,
     Wikidata ID, Crunchbase permalink)? Check `sameAs` in JSON-LD.
   - If no disambiguating identifiers exist and the name is ambiguous →
     **high** (AI assistants may confuse this brand with another).
   - If the name is unique (no other entities share it) → no finding.

9. **Check for consistent NAP (Name, Address, Phone) across web.**
   If the site is a local business, verify that the name, address, and
   phone number on the site match what's on Google Business, Yelp, or
   other directories found in the web search. Inconsistencies → medium.

10. **Emit findings.** Return an array of finding objects per
    `references/finding-schema.md`. Category is `"discoverability"`,
    sub_category is `"freshness"` or `"corroboration"`.

## Output

A JSON array of findings. See `references/finding-schema.md`.

## Severity guidelines

| Condition | Severity |
|-----------|----------|
| Key facts (what they do, location) with 0 external corroboration | high |
| Ambiguous brand name with no disambiguating identifiers | high |
| "Last updated" > 2 years on current product/service pages | high |
| Past events listed as upcoming in structured data | high |
| No freshness signal anywhere on the site | medium |
| Copyright year > 2 years old | medium |
| Most recent blog post > 12 months old | medium |
| Brand's own site not #1 search result for brand name | medium |
| NAP inconsistency across directories | medium |
| 1-2 independent sources (weak corroboration) | medium |
| Broken date-based URLs linked from root | low |

## Safety

- Read-only HTTP GET and web search only.
- Respect robots.txt for page fetches.
- Web searches are read-only queries; no accounts or authentication.
- Do not make more than 5 web search queries per audit.
