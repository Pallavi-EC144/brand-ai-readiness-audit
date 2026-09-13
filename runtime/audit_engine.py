"""Portable, read-only website audit engine used by the Vercel demo.
Standard-library only. The marketplace skills remain the agent-facing contract.
"""
from __future__ import annotations
import json, re, socket
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

UA = "BrandAIReadinessAudit/1.0 (+read-only; robots-aware)"
MAX_BYTES = 1_500_000
TIMEOUT = 8
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def normalize_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("url is required")
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    p = urlparse(value)
    if p.scheme not in {"http", "https"} or not p.hostname:
        raise ValueError("url must be a valid HTTP(S) URL")
    return value


def _host_is_public(host: str) -> bool:
    """Best-effort SSRF protection for a public website auditor."""
    h = host.lower().rstrip(".")
    if h in {"localhost", "localhost.localdomain"} or h.endswith(".local"):
        return False
    try:
        infos = socket.getaddrinfo(h, None)
        for info in infos:
            ip = info[4][0]
            import ipaddress
            addr = ipaddress.ip_address(ip)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
                return False
    except Exception:
        # Let the HTTP request provide the final failure; don't guess.
        pass
    return True


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title=[]; self.meta=[]; self.headings=[]; self.links=[]; self.images=[]
        self.iframes=[]; self.videos=[]; self.audios=[]; self.canvases=0; self.svg_text=0
        self.jsonlds=[]; self.text=[]; self._skip=0; self._in_title=False; self._in_jsonld=False; self._jsonbuf=[]
        self.main_text=[]

    def handle_starttag(self, tag, attrs):
        a=dict(attrs); t=tag.lower()
        if t in {"script","style","noscript"}: self._skip += 1
        if t=="title": self._in_title=True
        if t=="script" and a.get("type","").lower().split(";")[0]=="application/ld+json":
            self._in_jsonld=True; self._jsonbuf=[]
        if t in {"h1","h2","h3"}: self.headings.append((t,""))
        if t=="meta": self.meta.append(a)
        if t=="a" and a.get("href"): self.links.append(a.get("href"))
        if t=="img": self.images.append(a)
        if t=="iframe": self.iframes.append(a)
        if t=="video": self.videos.append(a)
        if t=="audio": self.audios.append(a)
        if t=="canvas": self.canvases += 1
        if t=="text" and self.svg_text>=0: self.svg_text += 1
        if self._skip==0 and t not in {"head","html","body"}: self.text.append(" ")

    def handle_endtag(self, tag):
        t=tag.lower()
        if t=="title": self._in_title=False
        if t=="script" and self._in_jsonld:
            self.jsonlds.append("".join(self._jsonbuf)); self._in_jsonld=False
        if t in {"script","style","noscript"}: self._skip=max(0,self._skip-1)

    def handle_data(self, data):
        if self._in_jsonld: self._jsonbuf.append(data)
        if self._skip==0:
            clean=re.sub(r"\s+"," ",data).strip()
            if clean:
                self.text.append(clean); self.text.append(" ")
        if self._in_title: self.title.append(data)
        if self.headings and self._skip==0:
            tag,text=self.headings[-1]
            if len(text)<500: self.headings[-1]=(tag,text+data)


def fetch(url: str):
    p=urlparse(url)
    if not _host_is_public(p.hostname or ""):
        raise ValueError("private or local hosts are not allowed")
    req=Request(url, headers={"User-Agent":UA, "Accept":"text/html,application/xhtml+xml"})
    with urlopen(req, timeout=TIMEOUT) as r:
        data=r.read(MAX_BYTES+1)
        return r.geturl(), r.status, dict(r.headers.items()), data[:MAX_BYTES]


def robots_allowed(root: str, target: str):
    p=urlparse(root); robots=f"{p.scheme}://{p.netloc}/robots.txt"
    rp=RobotFileParser()
    try:
        _,_,_,data=fetch(robots)
        rp.parse(data.decode("utf-8","ignore").splitlines())
        return rp.can_fetch(UA,target), True
    except Exception:
        # If robots.txt is unavailable, crawling is allowed by convention; failures are reported.
        return True, False


def finding(title, severity, evidence, action, category="discoverability", sub_category="general", pages=None, effort="medium"):
    return {"title":title,"severity":severity,"category":category,"sub_category":sub_category,
            "evidence":evidence,"suggested_action":{"summary":action,"priority":severity,"effort":effort},
            **({"pages_affected":pages} if pages else {})}


def parse_jsonld(parser):
    nodes=[]; malformed=0
    for raw in parser.jsonlds:
        try:
            obj=json.loads(raw); nodes.append(obj)
        except Exception: malformed += 1
    return nodes, malformed


def walk_json(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values(): yield from walk_json(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk_json(v)


def audit(root: str, max_pages: int=8):
    root=normalize_url(root)
    rootp=urlparse(root)
    host=rootp.netloc.lower()
    allowed, robots_found=robots_allowed(root, root)
    if not allowed: raise PermissionError("robots.txt disallows auditing the requested URL")
    queue=deque([root]); seen=set(); pages=[]; fetch_errors=[]
    while queue and len(pages)<max(1,min(int(max_pages),12)):
        u=queue.popleft()
        pu=urlparse(u)
        if pu.scheme not in {"http","https"} or pu.netloc.lower()!=host or u in seen: continue
        seen.add(u)
        ok,_=robots_allowed(root,u)
        if not ok: continue
        try:
            final,status,headers,data=fetch(u)
            ctype=headers.get("Content-Type","")
            if "html" not in ctype.lower() and not data.lstrip().startswith(b"<"): continue
            text=data.decode(headers.get_content_charset() if hasattr(headers,'get_content_charset') else 'utf-8',"ignore")
            parser=PageParser(); parser.feed(text)
            visible=" ".join(parser.text); visible=re.sub(r"\s+"," ",visible).strip()
            pages.append({"url":u,"final":final,"status":status,"headers":headers,"html":text,"parser":parser,"visible":visible})
            if len(pages)<min(8,max_pages):
                for href in parser.links:
                    v=urljoin(final,href).split("#",1)[0]
                    vp=urlparse(v)
                    if vp.scheme in {"http","https"} and vp.netloc.lower()==host and v not in seen:
                        queue.append(v)
        except Exception as e:
            fetch_errors.append(f"{u}: {type(e).__name__}")

    if not pages: raise RuntimeError("Could not fetch a readable HTML page from the target")
    findings=[]
    rootpage=pages[0]; p=rootpage["parser"]; html=rootpage["html"]; visible=rootpage["visible"]
    title=" ".join(p.title).strip(); metas={m.get("name","").lower():m.get("content","") for m in p.meta}; canon=next((m.get("content") for m in p.meta if m.get("property")=="og:url"),None)
    robots_meta=" ".join(metas.get("robots","").lower().split())

    if rootpage["status"]>=400:
        findings.append(finding("Homepage returns an error status", "critical", f"HTTP {rootpage['status']} for {rootpage['final']}.", "Fix the origin/server response so automated readers receive a successful page.", "discoverability","crawlability",[root],"high"))
    if "noindex" in robots_meta:
        findings.append(finding("Homepage is marked noindex", "high", f"Meta robots contains '{robots_meta}'.", "Remove noindex from pages intended to be discoverable and cited by AI systems.", "discoverability","crawlability",[root],"low"))
    if not title:
        findings.append(finding("Missing page title", "high", "No HTML <title> was found on the homepage.", "Add a concise, entity-specific <title> describing the organization and page purpose.","discoverability","content-extractability",[root],"low"))
    elif title.lower() in {"home","homepage","untitled","welcome"} or len(title)<8:
        findings.append(finding("Generic page title", "medium", f"Homepage title is '{title}'.", "Make the title identify the brand and the page's main purpose so extractors can classify it confidently.","discoverability","content-extractability",[root],"low"))
    if not metas.get("description"):
        findings.append(finding("Missing meta description", "medium", "No meta description was found on the homepage.", "Add a concise factual description of what the organization offers and who it serves.","discoverability","content-extractability",[root],"low"))
    if len(visible)<500:
        findings.append(finding("Thin server-delivered text", "high", f"Only about {len(visible)} characters of readable text were found in the initial HTML.", "Expose core value proposition, offerings, identity, and contact facts as server-delivered HTML rather than relying entirely on client-side rendering.","discoverability","render-gap",[root],"medium"))
    if "application/javascript" in rootpage["headers"].get("Content-Type","").lower():
        findings.append(finding("Unexpected non-HTML response", "high", f"Content-Type was {rootpage['headers'].get('Content-Type')}.", "Return HTML for the public page so automated readers can extract the page content.","discoverability","crawlability",[root],"medium"))

    h1=[x for x,t in p.headings if x=="h1"]
    if not h1: findings.append(finding("No primary heading", "medium", "No <h1> was found in the homepage HTML.", "Add one descriptive H1 stating the primary page/entity topic.","discoverability","content-extractability",[root],"low"))
    elif len(h1)>1: findings.append(finding("Multiple primary headings", "low", f"Found {len(h1)} H1 elements.", "Use one primary H1 and lower-level headings for supporting sections.","engagement","orientation",[root],"low"))

    if p.canvases:
        findings.append(finding("Canvas content may be opaque to extractors", "medium", f"Found {p.canvases} <canvas> element(s) in the initial HTML.", "Repeat any important facts shown on canvas in ordinary HTML text and accessible labels.","discoverability","content-extractability",[root],"medium"))
    if p.iframes:
        findings.append(finding("Important content may be inside third-party iframes", "medium", f"Found {len(p.iframes)} iframe(s); iframe contents are not part of the page's HTML.", "Expose essential business facts from embedded widgets as first-party HTML or structured data as well.","discoverability","content-extractability",[root],"medium"))
    if p.videos and not re.search(r"caption|transcript", html, re.I):
        findings.append(finding("Video content lacks an obvious transcript/caption signal", "medium", f"Found {len(p.videos)} video element(s) without an obvious caption/transcript reference.", "Provide captions and a text transcript for substantive video information.","discoverability","content-extractability",[root],"medium"))
    pdfs=[urljoin(root,x) for x in p.links if re.search(r"\.pdf(?:$|[?#])",x,re.I)]
    if pdfs: findings.append(finding("Important content may be PDF-only", "low", f"Homepage links to {len(pdfs)} PDF document(s).", "Keep critical facts such as pricing, services, hours, and product details in HTML too; use PDFs as supporting documents.","discoverability","content-extractability",[root],"medium"))

    nodes, malformed=parse_jsonld(p)
    if malformed:
        findings.append(finding("Malformed JSON-LD", "high", f"{malformed} JSON-LD block(s) could not be parsed as JSON.", "Fix JSON syntax and validate the structured data before deployment.","discoverability","structured-data",[root],"medium"))
    allnodes=[n for obj in nodes for n in walk_json(obj)]
    types=[]
    for n in allnodes:
        t=n.get("@type") if isinstance(n,dict) else None
        if isinstance(t,list): types.extend(t)
        elif t: types.append(t)
    orgs=[n for n in allnodes if isinstance(n,dict) and any(t in (n.get("@type") if isinstance(n.get("@type"),list) else [n.get("@type")]) for t in ["Organization","LocalBusiness"]) ]
    if not nodes:
        findings.append(finding("No JSON-LD structured data on homepage", "medium", "No application/ld+json block was found. Absence is not automatically wrong, but it leaves fewer explicit machine-readable identity signals.", "Add appropriate schema.org JSON-LD for the site's primary entity, such as Organization or LocalBusiness, including stable identity links where applicable.","discoverability","structured-data",[root],"medium"))
    elif not orgs:
        findings.append(finding("No explicit organization identity in JSON-LD", "medium", f"JSON-LD types found: {', '.join(map(str,types[:8])) or 'none'}; no Organization/LocalBusiness node was detected.", "Add a suitable Organization or LocalBusiness entity with name, url, logo, and stable identity signals where applicable.","discoverability","entity-identity",[root],"medium"))
    else:
        for o in orgs:
            if not o.get("name"): findings.append(finding("Organization structured data lacks a name", "critical", "An Organization/LocalBusiness node exists but has no name property.", "Add the canonical public organization name to the entity node.","discoverability","structured-data",[root],"low")); break
            if not o.get("url"): findings.append(finding("Organization structured data lacks a URL", "medium", "Organization/LocalBusiness JSON-LD has no url property.", "Set url to the canonical homepage for stable entity association.","discoverability","entity-identity",[root],"low")); break
            if not o.get("sameAs"): findings.append(finding("Organization has no sameAs identity links", "medium", "The primary organization entity has no sameAs property.", "Add verified official profiles or authoritative identity references to reduce entity ambiguity.","discoverability","entity-identity",[root],"low")); break

    # Freshness signals
    dates=re.findall(r"\b(?:20\d{2})[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b", visible, re.I)
    modified=rootpage["headers"].get("Last-Modified")
    if not dates and not modified and not re.search(r"updated|last modified|dateModified|datePublished",html,re.I):
        findings.append(finding("No clear freshness signal", "medium", "No visible date, Last-Modified header, or obvious updated/published signal was detected on the homepage.", "Expose meaningful publication or last-updated dates on time-sensitive content and in structured data where appropriate.","discoverability","freshness",[root],"low"))

    # Engagement/orientation
    cta=re.search(r"\b(get started|learn more|contact us|book|buy|shop|sign up|request|demo|explore|download|apply)\b", visible, re.I)
    if not cta:
        findings.append(finding("No obvious next action on the homepage", "medium", "No common action-oriented CTA phrase was detected in extracted homepage text.", "Add one clear primary next step aligned with the visitor's likely intent, and support it with a secondary path where needed.","engagement","next-action",[root],"low"))
    nav=re.search(r"<nav\b|aria-label=[\"'](?:main|primary|navigation)",html,re.I)
    if not nav:
        findings.append(finding("Navigation is not clearly marked", "low", "No <nav> element or obvious primary-navigation ARIA label was detected.", "Use semantic navigation markup with descriptive labels so visitors and automated agents can understand site structure.","engagement","navigation",[root],"low"))
    if not re.search(r"privacy", visible, re.I):
        findings.append(finding("No obvious privacy/trust page link", "low", "No privacy-related link text was detected in the homepage's extracted text.", "Provide easy access to privacy and other relevant trust information where appropriate.","engagement","trust",[root],"low"))

    # Cross-page title duplication
    titles={x["url"]:" ".join(x["parser"].title).strip() for x in pages}
    nonempty=[t for t in titles.values() if t]
    if len(nonempty)>=3 and len(set(t.lower() for t in nonempty))==1:
        findings.append(finding("Multiple crawled pages share the same title", "medium", f"{len(nonempty)} crawled HTML pages use the same title.", "Give each important page a distinct, descriptive title reflecting its content and entity context.","discoverability","content-extractability",list(titles)[:8],"low"))

    # Robots/sitemap signals
    if not robots_found:
        findings.append(finding("robots.txt could not be verified", "low", "The audit could not retrieve robots.txt; crawling permission was therefore not explicitly confirmed from that file.", "Publish a reachable robots.txt with deliberate crawler guidance and a sitemap reference where appropriate.","discoverability","crawlability",[root],"low"))
    sitemap=urljoin(root,"/sitemap.xml")
    try:
        _,st,_,_=fetch(sitemap)
        if st>=400: raise Exception()
    except Exception:
        findings.append(finding("No reachable sitemap.xml detected", "low", "A GET request to /sitemap.xml did not return a readable response.", "Publish an XML sitemap for important public URLs, especially on larger sites.","discoverability","crawlability",[root],"low"))

    # Deduplicate by title and page.
    unique=[]; keys=set()
    for f in findings:
        k=(f["title"], tuple(f.get("pages_affected",[])[:2]))
        if k not in keys: keys.add(k); unique.append(f)
    unique.sort(key=lambda f:SEVERITY_ORDER[f["severity"]])
    for i,f in enumerate(unique,1): f["id"]=f"F-{i:03d}"
    counts={s:sum(f["severity"]==s for f in unique) for s in SEVERITY_ORDER}
    site=urlparse(root).netloc
    return {"site":site,"audited_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z"),
            "summary":{"total_findings":len(unique),**counts},"findings":unique,
            "audit_metadata":{"pages_crawled":len(pages),"max_pages":max_pages,"read_only":True,"robots_checked":robots_found,
                               "notes":["Static HTML audit; client-side content that is not present in initial HTML may be under-detected."]}}
