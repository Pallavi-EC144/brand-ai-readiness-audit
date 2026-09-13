#!/usr/bin/env python3
"""
check_engagement.py — Analyze on-site engagement factors in page HTML.

Checks viewport meta, navigation, CTAs, trust signals, mobile
responsiveness, performance indicators, and content hierarchy.

Usage:
    python3 check_engagement.py <url>

Outputs JSON with diagnostic details the engagement-audit skill can use
to build findings.
"""

import sys
import re
import json
import argparse
import urllib.request
from html.parser import HTMLParser


def fetch_html(url: str) -> tuple[str, str, bool]:
    """Fetch URL, return (html, final_url, is_https)."""
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BrandAIAuditBot/1.0 (audit; read-only)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace"), resp.url, resp.url.startswith("https://")
    except Exception:
        return "", url, False


class EngagementAnalyzer(HTMLParser):
    CTA_KEYWORDS = [
        "get started", "sign up", "signup", "register", "contact us",
        "contact", "buy now", "order", "subscribe", "learn more",
        "read more", "get a quote", "request", "book now", "book",
        "try free", "try now", "start free", "join", "enroll",
        "shop now", "view more", "explore", "demo", "download",
        "apply", "donate", "get quote", "call now", "schedule",
    ]

    def __init__(self):
        super().__init__()
        self.in_script = False
        self.in_style = False
        self.viewport_meta = None
        self.has_nav = False
        self.nav_link_count = 0
        self.has_footer = False
        self.footer_contact = {"email": False, "phone": False, "address": False}
        self.h1_texts = []
        self.h2_count = 0
        self.h3_count = 0
        self.heading_skips = False
        self.current_h1 = None
        self.in_h1 = False
        self.ctas_found = []
        self.has_contact_link = False
        self.contact_methods = {"email_link": False, "phone_link": False, "form": False}
        self.social_links = []
        self.privacy_policy_link = False
        self.terms_link = False
        self.testimonials_signals = False
        self.review_signals = False
        self.favicon = False
        self.render_blocking_scripts = 0
        self.external_scripts = 0
        self.internal_scripts = 0
        self.deferred_scripts = 0
        self.async_scripts = 0
        self.imgs_without_dimensions = 0
        self.imgs_total = 0
        self.preload_links = 0
        self.font_display_swap = False
        self.viewport_has_media_queries = False
        self.style_blocks = []
        self.in_style_block = False
        self._style_parts = []
        self.nav_items = 0
        self.in_nav = False
        self.in_footer = False
        self.title = None
        self.in_title = False
        self._title_parts = []
        self.css_has_media_query = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "script":
            self.in_script = True
            src = attrs_dict.get("src", "")
            is_async = "async" in attrs
            is_defer = "defer" in attrs
            if src:
                if src.startswith("http") and not src.startswith(window_location_guess):
                    self.external_scripts += 1
                else:
                    self.internal_scripts += 1
                if not is_async and not is_defer:
                    self.render_blocking_scripts += 1
            else:
                if not is_async and not is_defer:
                    self.render_blocking_scripts += 1
            if is_defer:
                self.deferred_scripts += 1
            if is_async:
                self.async_scripts += 1
        elif tag == "style":
            self.in_style = True
            self.in_style_block = True
            self._style_parts = []
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            viewport = attrs_dict.get("content", "")
            if name == "viewport":
                self.viewport_meta = viewport
            elif name == "description":
                pass
        elif tag == "title":
            self.in_title = True
        elif tag == "nav":
            self.has_nav = True
            self.in_nav = True
        elif tag == "footer":
            self.has_footer = True
            self.in_footer = True
        elif tag == "h1":
            self.in_h1 = True
        elif tag == "h2":
            self.h2_count += 1
        elif tag == "h3":
            self.h3_count += 1
        elif tag == "h4":
            if self.h2_count == 0 and self.h3_count == 0:
                self.heading_skips = True
        elif tag == "img":
            self.imgs_total += 1
            if "width" not in attrs_dict or "height" not in attrs_dict:
                self.imgs_without_dimensions += 1
        elif tag == "link":
            rel = attrs_dict.get("rel", "").lower()
            if rel == "preload":
                self.preload_links += 1
            elif rel == "icon" or rel == "shortcut icon":
                self.favicon = True
            elif rel == "stylesheet":
                media = attrs_dict.get("media", "")
                if "max-width" in media or "min-width" in media:
                    self.css_has_media_query = True
        elif tag == "a":
            href = attrs_dict.get("href", "")
            text = attrs_dict.get("aria-label", "")

            if self.in_nav:
                self.nav_items += 1

            # Check for CTAs
            # (text content check happens in handle_data for the link text)

            if "contact" in href.lower() or "contact" in text.lower():
                self.has_contact_link = True
            if href.startswith("mailto:"):
                self.contact_methods["email_link"] = True
                if self.in_footer:
                    self.footer_contact["email"] = True
            if href.startswith("tel:"):
                self.contact_methods["phone_link"] = True
                if self.in_footer:
                    self.footer_contact["phone"] = True
            if "privacy" in href.lower():
                self.privacy_policy_link = True
            if "terms" in href.lower() or "tos" in href.lower():
                self.terms_link = True
            if any(social in href for social in [
                "facebook.com", "twitter.com", "x.com", "instagram.com",
                "linkedin.com", "youtube.com", "tiktok.com", "github.com",
                "pinterest.com"
            ]):
                self.social_links.append(href)
        elif tag == "form":
            self.contact_methods["form"] = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False
            self.in_style_block = False
            style_text = "".join(self._style_parts)
            self.style_blocks.append(style_text)
            if "@media" in style_text:
                self.css_has_media_query = True
            if "font-display" in style_text and "swap" in style_text:
                self.font_display_swap = True
        elif tag == "nav":
            self.in_nav = False
        elif tag == "footer":
            self.in_footer = False
        elif tag == "h1":
            self.in_h1 = False
            if self.current_h1:
                self.h1_texts.append(self.current_h1.strip())
                self.current_h1 = None
        elif tag == "title":
            self.in_title = False
            self.title = "".join(self._title_parts).strip()
            self._title_parts = []

    def handle_data(self, data):
        if self.in_script:
            return
        if self.in_style_block:
            self._style_parts.append(data)
            return
        stripped = data.strip()
        if not stripped:
            return

        if self.in_h1:
            self.current_h1 = (self.current_h1 or "") + stripped

        if self.in_title:
            self._title_parts.append(stripped)

        # Check for CTA keywords in link/button text
        lower = stripped.lower()
        for kw in self.CTA_KEYWORDS:
            if kw in lower and len(stripped) < 100:
                self.ctas_found.append(stripped[:80])
                break

        # Check for testimonial/review signals
        if any(w in lower for w in ["testimonial", "what our customers", "what people say"]):
            self.testimonials_signals = True
        if any(w in lower for w in ["review", "rating", "stars", "out of 5"]):
            self.review_signals = True

        # Check footer for contact text
        if self.in_footer:
            if re.search(r'[\w.-]+@[\w.-]+\.\w+', stripped):
                self.footer_contact["email"] = True
            if re.search(r'\+?\d[\d\s\-()]{7,}', stripped):
                self.footer_contact["phone"] = True


# Global for script source comparison (simplified)
window_location_guess = "https://"


def main():
    parser = argparse.ArgumentParser(
        description="Analyze engagement factors in page HTML"
    )
    parser.add_argument("url", help="URL to analyze")
    args = parser.parse_args()

    html, final_url, is_https = fetch_html(args.url)
    if not html:
        print(json.dumps({"error": "Failed to fetch URL", "url": args.url}, indent=2))
        sys.exit(1)

    analyzer = EngagementAnalyzer()
    analyzer.feed(html)

    # Check for default framework titles
    default_titles = ["create react app", "vite + react", "vite app", "next.js",
                      "nuxt", "vue app", "angular app", "webpack app"]
    is_default_title = False
    if analyzer.title:
        title_lower = analyzer.title.lower().strip()
        for dt in default_titles:
            if dt in title_lower:
                is_default_title = True
                break

    # Check for media queries in inline styles
    all_css = " ".join(analyzer.style_blocks)
    has_media_queries = "@media" in all_css or analyzer.css_has_media_query

    # Determine mobile readiness
    has_viewport = analyzer.viewport_meta is not None
    mobile_ready = has_viewport and (has_media_queries or "width=device-width" in (analyzer.viewport_meta or ""))

    result = {
        "url": final_url,
        "is_https": is_https,
        "viewport_meta": analyzer.viewport_meta,
        "mobile_ready": mobile_ready,
        "has_nav": analyzer.has_nav,
        "nav_item_count": analyzer.nav_items,
        "has_footer": analyzer.has_footer,
        "footer_contact": analyzer.footer_contact,
        "h1_texts": analyzer.h1_texts,
        "h1_count": len(analyzer.h1_texts),
        "h2_count": analyzer.h2_count,
        "h3_count": analyzer.h3_count,
        "heading_skips_levels": analyzer.heading_skips,
        "ctas_found": list(set(analyzer.ctas_found))[:10],
        "cta_count": len(set(analyzer.ctas_found)),
        "has_contact_link": analyzer.has_contact_link,
        "contact_methods": analyzer.contact_methods,
        "social_links": list(set(analyzer.social_links))[:10],
        "social_link_count": len(set(analyzer.social_links)),
        "privacy_policy_link": analyzer.privacy_policy_link,
        "terms_link": analyzer.terms_link,
        "testimonials_found": analyzer.testimonials_signals,
        "reviews_found": analyzer.review_signals,
        "has_favicon": analyzer.favicon,
        "title": analyzer.title,
        "is_default_title": is_default_title,
        "render_blocking_scripts": analyzer.render_blocking_scripts,
        "external_scripts": analyzer.external_scripts,
        "deferred_scripts": analyzer.deferred_scripts,
        "async_scripts": analyzer.async_scripts,
        "imgs_total": analyzer.imgs_total,
        "imgs_without_dimensions": analyzer.imgs_without_dimensions,
        "preload_links": analyzer.preload_links,
        "font_display_swap": analyzer.font_display_swap,
        "css_has_media_queries": has_media_queries,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
