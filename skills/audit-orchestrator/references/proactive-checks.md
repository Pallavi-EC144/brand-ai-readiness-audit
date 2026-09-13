# Proactive Checks

These are checks the orchestrator runs after collecting all sub-skill
findings. They identify opportunities to strengthen discoverability or
engagement even where no explicit defect was found. Add each as a finding
with severity `low` and evidence explaining the opportunity (not a defect).

## Discoverability proactive checks

1. **Knowledge graph presence.** If no `sameAs` link to Wikidata or
   Wikipedia was found in structured data, and the brand appears notable
   enough (has a website, products, history), recommend creating a
   Wikidata entry and/or Wikipedia article. Evidence: "No Wikidata or
   Wikipedia entity found in sameAs links; brand has products/services
   that would qualify for a knowledge graph entry."

2. **FAQ page.** If no `FAQPage` JSON-LD was found on any crawled page,
   recommend adding an FAQ section with `FAQPage` structured data. This
   directly feeds AI assistant Q&A retrieval. Evidence: "No FAQPage
   schema found; AI assistants frequently answer brand-related questions
   by matching FAQ content."

3. **Open Graph and Twitter Card tags.** If `<meta property="og:">` or
   `<meta name="twitter:">` tags are missing, recommend adding them for
   better link previews when the brand is shared or cited. Evidence:
   "No Open Graph tags found; link previews on social and messaging
   platforms will show generic/empty cards."

4. **Hreflang / international signals.** If the site appears to serve
   multiple languages (detect via `<html lang="">` or multiple
   language-specific paths) but has no `<link rel="hreflang">` tags,
   recommend adding them.

5. **Atom/RSS feed.** If the site has a blog or news section but no
   RSS/Atom feed link in `<head>`, recommend adding one. Feeds are still
   consumed by some aggregators and monitoring tools.

## Engagement proactive checks

6. **Schema.org `SiteNavigationElement`.** If navigation exists but has
   no `SiteNavigationElement` JSON-LD, recommend adding it to help
   machines understand the site's information architecture.

7. **Accessible design signals.** If no `aria-label` or `aria-labelledby`
   attributes were found on interactive elements, recommend adding ARIA
   labels for accessibility (which also helps crawlers understand element
   purpose).

8. **Content above the fold.** If the hero section exists but contains
   only an image (no text), recommend adding a text overlay or adjacent
   text heading so the value proposition is immediately visible.

9. **Internal linking depth.** If the root page links to fewer than 3
   internal pages, recommend adding more internal links to help visitors
   and crawlers discover deeper content.

10. **Social proof.** If the page is commercial (has products/services)
    but no customer reviews, ratings, or testimonials were found, recommend
    adding social proof elements.
