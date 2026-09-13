---
name: structured-data-audit
description: >
  Audits a website for the presence, validity, and coverage of structured
  data (schema.org JSON-LD, Microdata, RDFa) that helps AI assistants and
  search engines reliably extract facts about the brand, its products,
  services, events, and organizational identity. Detects missing,
  malformed, or incomplete structured data that leads to facts being
  missed or misattributed. Use as part of the brand-ai-readiness-audit
  marketplace.
license: MIT
allowed-tools:
  - WebFetch
  - WebSearch
---

# Structured Data Audit

## When to use

Invoke this skill after the crawl-render audit confirms the page is
reachable. This skill checks whether the page's key facts are encoded in
machine-readable structured data that AI assistants can reliably extract.

## Inputs

- **url** (required) — root URL to audit
- **depth** (optional, default `1`) — pages to crawl beyond root
- **max-pages** (optional, default `10`) — max pages to fetch

## Procedure

1. **Fetch the root page HTML.**

2. **Detect JSON-LD blocks.** Search for `<script type="application/ld+json">`
   tags. For each block found:
   - Parse the JSON. If parsing fails, record a **high** finding (malformed
     JSON-LD).
   - Identify the `@type` of each node. Common valuable types:
     `Organization`, `LocalBusiness`, `Product`, `Offer`, `Service`,
     `Event`, `Article`, `BreadcrumbList`, `WebSite`, `FAQPage`,
     `Person`, `Place`, `Review`, `AggregateRating`.
   - For `Organization`/`LocalBusiness` types, check for these key
     properties and flag missing ones:
     - `name` (critical if missing)
     - `url` (high if missing)
     - `logo` (medium if missing)
     - `sameAs` (medium — links to official social profiles for entity
       disambiguation)
     - `address` / `areaServed` (medium for local businesses)
     - `telephone` / `email` (low-medium for local businesses)
     - `description` (low)
   - For `Product` types, check for:
     - `name` (critical)
     - `offers` / `Offer` with `price` and `priceCurrency` (high)
     - `description` (medium)
     - `image` (medium)
     - `brand` (medium)
     - `aggregateRating` (low)

3. **Detect Microdata.** Search for `itemscope`, `itemtype`, and `itemprop`
   attributes in the HTML. If present:
   - Record the types used.
   - Note that Microdata is less widely supported than JSON-LD — recommend
     migrating to JSON-LD if Microdata is the only format.

4. **Detect RDFa.** Search for `vocab` or `typeof` attributes. Note if
   RDFa is the only structured data format present.

5. **Assess coverage.** If no structured data is found on the root page,
   record a **high** finding (no structured data at all).

6. **Check for organization identity signals.** If `Organization` or
   `LocalBusiness` JSON-LD exists, verify:
   - `sameAs` links to at least 2 external authoritative profiles
     (Wikipedia, social media, Google Business). Fewer than 2 = medium
     finding (weak entity disambiguation).
   - `@id` is present and stable (a unique URI for the entity). Missing
     `@id` = low finding.

7. **Crawl additional pages** (up to max-pages). For product pages, event
   pages, article pages, check whether page-specific structured data is
   present. If 0/N product pages have `Product` JSON-LD, record a high
   finding.

8. **Validate against schema.org.** For each JSON-LD node, check that:
   - The `@type` is a valid schema.org type.
   - Required properties for that type are present.
   - Property values match expected types (e.g. `offers` should contain
     an `Offer` object, not a string).
   Use `references/schema-org-types.md` for the validation rules.

9. **Emit findings.** Return an array of finding objects per
   `references/finding-schema.md`. Category is always
   `"discoverability"`, sub_category is `"structured-data"`.

## Output

A JSON array of findings. See `references/finding-schema.md`.

## Severity guidelines

| Condition | Severity |
|-----------|----------|
| No structured data on any page | high |
| Malformed JSON-LD (parse error) | high |
| Product pages missing Product/Offer JSON-LD | high |
| No Organization/LocalBusiness identity on root | high |
| Missing `name` in Organization | critical |
| Missing `sameAs` or < 2 external profiles | medium |
| Missing `logo`, `url`, `address` | medium |
| Missing canonical `@id` | low |
| Microdata only (no JSON-LD) | low |

## Safety

- Read-only HTTP GET only.
- Respect robots.txt.
