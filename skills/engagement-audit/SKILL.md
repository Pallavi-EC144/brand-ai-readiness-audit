---
name: engagement-audit
description: >
  Audits a website's on-site engagement factors — the things that
  determine whether a visitor who arrives stays, orients themselves, and
  takes action. Checks page load performance, mobile responsiveness,
  clear value proposition, navigation clarity, content hierarchy, call-
  to-action presence, context retention across pages, and trust signals.
  Detects why visitors who arrive don't engage. Use as part of the
  brand-ai-readiness-audit marketplace.
license: MIT
allowed-tools:
  - WebFetch
  - WebSearch
---

# Engagement Audit

## When to use

Invoke this skill as the final sub-skill in the audit pipeline. It focuses
on the on-site experience — whether the page orients visitors, communicates
value clearly, and provides frictionless paths to action.

## Inputs

- **url** (required) — root URL to audit
- **depth** (optional, default `1`) — pages to crawl beyond root
- **max-pages** (optional, default `10`) — max pages to fetch

## Procedure

### A. First Impression & Orientation

1. **Fetch the root page HTML.** Assess the above-the-fold experience
   (what a visitor sees before scrolling):

   - **Value proposition clarity.** Is there a clear `<h1>` or hero
     heading that states what the brand does and who it's for? Look for
     `<h1>` text within the first 2000 chars of `<body>`.
     - Missing or generic `<h1>` ("Welcome", "Home") → **high**.
     - `<h1>` exists but doesn't state what the brand does → medium.

   - **Hero section.** Is there a hero area with a primary message and a
     call-to-action? Check for:
     - A prominent heading or tagline.
     - A primary CTA button or link (`<a>` or `<button>` with action
       text like "Get started", "Learn more", "Contact us",
       "Buy now", "Sign up").
     - Missing CTA in hero → medium.

   - **Visual hierarchy.** Check for a logical heading structure:
     `<h1>` → `<h2>` → `<h3>` without skipping levels. Skipping levels
     (e.g. `<h1>` straight to `<h4>`) → low.

### B. Navigation & Wayfinding

2. **Check primary navigation.** Look for `<nav>` elements or a main
   menu:
   - Missing `<nav>` element → medium (no semantic navigation landmark).
   - Navigation links are ambiguous ("Solutions", "Resources" with no
     sub-context) → low.
   - Navigation has > 8 top-level items → low (cognitive overload).

3. **Check breadcrumb navigation** on non-root pages (if crawled):
   - Missing breadcrumbs on deep pages → low.
   - Breadcrumbs exist but are not in structured data
     (`BreadcrumbList` JSON-LD) → low.

4. **Context retention across pages.** If depth ≥ 1, crawl 2-3 internal
   pages and check:
   - Does each page have a consistent header/nav with the brand name or
     logo? Inconsistent branding across pages → medium.
   - Does each page have a clear `<h1>` indicating which section the
     visitor is in? Missing → medium.
   - Is there a consistent footer with contact info, social links, and
     navigation? Missing footer → low.

### C. Call-to-Action & Conversion Paths

5. **Identify CTAs across the page.** Search for action-oriented text in
   `<a>`, `<button>` elements:
   - 0 CTAs on the entire root page → **high** (visitor has no clear next
     step).
   - CTAs only below the fold (requires scrolling to find any action) →
     medium.
   - Multiple competing CTAs with equal visual weight → low (decision
     paralysis).

6. **Check for contact accessibility.** Look for:
   - A contact page link in nav or footer.
   - Email address or phone number in text (not just in an image).
   - A contact form.
   - Missing all contact mechanisms → **high**.
   - Contact info only in footer, not easily discoverable → low.

### D. Trust & Credibility Signals

7. **Check for trust signals:**
   - SSL/HTTPS (the URL starts with `https://`). If HTTP → **high**
     (browsers flag as insecure).
   - Customer testimonials, reviews, or case studies on the page.
     Missing on a commercial site → medium.
   - Social proof indicators (customer logos, review counts, user
     numbers). Missing → low.
   - Privacy policy and terms of service links. Missing → medium.
   - Professional design quality signal: consistent favicon, no
     "default template" look (hard to detect from HTML, but check for
     framework default titles like "Create React App" or
     "Vite + React" in `<title>`) → medium if detected.

### E. Mobile Responsiveness

8. **Check responsive design signals:**
   - `<meta name="viewport">` tag present. Missing → **high** (page
     won't render correctly on mobile).
   - CSS uses `@media` queries (check in `<style>` blocks or linked
     stylesheets). If no media queries and no viewport meta → high.
   - `max-width` or responsive grid patterns in inline styles. Absence
     is a weak signal → low.

### F. Performance Indicators

9. **Check for performance red flags in the HTML:**
   - Large unoptimized images: `<img>` tags without `width`/`height`
     attributes (causes layout shift) → low.
   - Render-blocking resources: multiple `<script>` tags in `<head>`
     without `defer` or `async` → medium.
   - Excessive third-party scripts: count `<script src>` from external
     domains. > 10 external scripts → medium.
   - No `<link rel="preload">` for critical resources → low.
   - System fonts vs web fonts: if using web fonts, check for
     `font-display: swap` in CSS. Missing → low (FOIT causes blank
     text during load).

10. **Emit findings.** Return an array of finding objects per
    `references/finding-schema.md`. Category is `"engagement"`,
    sub_category is one of: `"orientation"`, `"navigation"`,
    `"conversion"`, `"trust"`, `"mobile"`, `"performance"`.

## Output

A JSON array of findings. See `references/finding-schema.md`.

## Severity guidelines

| Condition | Severity |
|-----------|----------|
| No viewport meta tag (mobile broken) | high |
| HTTP instead of HTTPS | high |
| No CTA anywhere on root page | high |
| No contact mechanism at all | high |
| Missing or generic `<h1>` (no value proposition) | high |
| Default framework title ("Create React App", "Vite App") | medium |
| No `<nav>` semantic element | medium |
| Missing meta description | medium |
| No testimonials/reviews on commercial site | medium |
| No privacy policy link | medium |
| Many render-blocking scripts in `<head>` | medium |
| > 10 external third-party scripts | medium |
| Branding inconsistent across pages | medium |
| CTAs only below the fold | medium |
| Skipped heading levels | low |
| > 8 top-level nav items | low |
| Missing breadcrumbs on deep pages | low |
| Missing footer | low |
| Images without width/height | low |

## Safety

- Read-only HTTP GET only.
- Respect robots.txt.
- No user simulation, no interaction, no form submission.
