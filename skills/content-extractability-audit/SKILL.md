---
name: content-extractability-audit
description: >
  Audits whether the key facts on a website are present in plain,
  machine-readable text that AI assistants can extract, or whether they
  are locked inside non-text formats (images, videos, PDFs, canvas,
  iframe-embedded content, interactive widgets) that automated readers
  cannot interpret. Detects facts that are visible to humans but invisible
  to machines. Use as part of the brand-ai-readiness-audit marketplace.
license: MIT
allowed-tools:
  - WebFetch
  - WebSearch
---

# Content Extractability Audit

## When to use

Invoke this skill after the crawl-render audit confirms the page is
reachable. This skill checks whether the facts a visitor can see are also
available to a machine reader — or locked in non-text containers.

## Inputs

- **url** (required) — root URL to audit
- **depth** (optional, default `1`) — pages to crawl beyond root
- **max-pages** (optional, default `10`) — max pages to fetch

## Procedure

1. **Fetch the root page HTML** (server-delivered, pre-JS).

2. **Extract the visible text content** from the raw HTML:
   - Strip `<script>`, `<style>`, `<svg>`, `<noscript>` tags.
   - Extract text from `<body>` (or `<main>`, `<article>` if present).
   - Record total visible text length (chars).
   - If < 500 chars of meaningful text, flag as **high** finding
     (thin text content for machines).

3. **Identify key facts and check their text availability.** Look for
   these common fact types and whether they appear as extractable text:

   | Fact type | Where it often lives | Check |
   |-----------|---------------------|-------|
   | Price / cost | Image, JS-rendered widget, SVG | Is it in a text node? |
   | Business hours | Image, Google Maps embed | Is it in text or `<time>`? |
   | Address / location | Map embed, image | Is it in text or structured data? |
   | Phone / email | Image, JS obfuscation | Is it in a `href` or text node? |
   | Product specs | Comparison table in canvas/img | Is it in `<td>` text? |
   | Reviews / ratings | Third-party widget iframe | Is rating in text or JSON-LD? |
   | Menu / service list | PDF, image, Flash-like embed | Is it in HTML text? |
   | Company description | Video, hero image text | Is it in `<p>` text? |

   For each fact type found on the page (by visual inspection of the HTML
   structure), determine whether it is available as text. If a fact appears
   to be locked in a non-text format, record a finding.

4. **Detect non-text content containers.** Scan the HTML for:
   - `<img>` tags that appear to contain textual information (images with
     `alt` text that describes data, e.g. `alt="pricing table"`,
     `alt="our hours"`). If the `alt` is generic or missing, flag as
     medium. If `alt` contains the full info, note as low (alt text
     partially compensates but is less reliable than real text).
   - `<canvas>` elements — content is script-rendered and invisible to
     non-JS readers. Flag if canvas appears to hold key content.
   - `<iframe>` embeds for third-party widgets (review widgets, map
     embeds, booking widgets). The content inside the iframe is on a
     different origin and not readable by the page's crawler. Flag as
     medium.
   - `<video>` / `<audio>` without captions or transcripts. Flag as
     medium if the video appears to contain substantive info.
   - PDF links (`<a href="*.pdf">`) for content that should be HTML
     (menus, pricing, specs). Flag as medium — PDFs are partially
     extractable but not as reliable as HTML text.
   - SVG text (`<text>` inside `<svg>`) — some extractors handle this,
     many don't. Flag as low.

5. **Check for JS-based text obfuscation.** Look for patterns where text
   is constructed at runtime:
   - Email addresses split across JS variables and concatenated.
   - Phone numbers rendered via document.write or innerHTML assignment.
   - Content injected via AJAX/fetch after page load.
   These are invisible to a static HTML fetch. Flag as **high**.

6. **Check heading structure.** Count `<h1>`, `<h2>`, `<h3>` tags:
   - 0 `<h1>` tags → medium finding (no primary heading for machines).
   - Multiple `<h1>` tags → low finding (ambiguous hierarchy).
   - Headings used for styling rather than structure (e.g. `<h4>` inside
     a footer with no `<h1>`-`<h3>` above) → low.

7. **Check for descriptive page `<title>` and `<meta name="description">`.**
   - Missing `<title>` → high.
   - Generic `<title>` (just "Home" or the domain name) → medium.
   - Missing meta description → medium (AI assistants and search engines
     use this for summarization).
   - Generic meta description → low.

8. **Check for clear NLP-friendly fact statements.** Scan the text content
   for sentences that state key facts in plain declarative form:
   - "We are a [type] company based in [location]"
   - "Our products include [X, Y, Z]"
   - "Founded in [year]"
   - "Contact us at [phone/email]"
   If none of these patterns exist and the page is a brand/business site,
   flag as medium (facts are implied but not explicitly stated).

9. **Emit findings.** Return an array of finding objects per
   `references/finding-schema.md`. Category is `"discoverability"`,
   sub_category is `"content-extractability"` or `"engagement"` for
   heading/title issues that affect user orientation.

## Output

A JSON array of findings. See `references/finding-schema.md`.

## Severity guidelines

| Condition | Severity |
|-----------|----------|
| Key facts (price, hours, address) locked in images with no alt text | high |
| Email/phone obfuscated via JS only | high |
| < 500 chars of meaningful text on root page | high |
| Missing `<title>` tag | high |
| Facts in iframe-embedded third-party widgets only | medium |
| Missing meta description | medium |
| No `<h1>` heading | medium |
| Key content in PDF instead of HTML | medium |
| Generic `<title>` ("Home", domain name only) | medium |
| Facts in `<img>` but alt text compensates | low |
| SVG text for key content | low |
| Multiple `<h1>` tags | low |

## Safety

- Read-only HTTP GET only.
- Respect robots.txt.
