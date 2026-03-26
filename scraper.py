import os
import re
import time
import smtplib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from email.mime.text import MIMEText

EMAIL_ADDRESS = os.environ["EMAIL_ADDRESS"]
EMAIL_APP_PASSWORD = os.environ["EMAIL_APP_PASSWORD"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

SEARCH_QUERIES = [
    '"UKG implementation"',
    '"UKG migration"',
    '"UKG rollout"',
    '"UKG go live"',
    '"Kronos to UKG"',
    '"UKG Dimensions implementation"',
    '"UKG Ready implementation"',
    '"replacing Kronos"',
    '"workforce management transformation" UKG',
]

EXCLUDED = [
    "ascend", "mosaic", "deloitte", "ey", "kpmg", "pwc", "rsm",
    "accenture", "capgemini", "infosys", "tcs", "wipro", "cognizant",
    "teksystems", "insight global", "kforce", "randstad", "robert half",
    "apex systems", "collabera", "alight", "guidehouse", "hr path",
    "topbloc", "workforce insight", "jobot", "planet technology"
]

GOOD_TERMS = [
    "implementation", "migration", "rollout", "go live", "go-live",
    "upgrade", "deployment", "transformation", "selecting", "selection",
    "replacing", "replacement", "dimensions", "ready", "workforce management"
]

BAD_TERMS = [
    "partner", "consulting", "consultant", "staffing", "recruiter",
    "agency", "vendor", "system integrator", "implementation partner"
]

PUBLIC_DOMAINS_TO_PRIORITIZE = [
    "indeed.com",
    "ziprecruiter.com",
    "glassdoor.com",
    "lever.co",
    "greenhouse.io",
    "workdayjobs.com",
    "myworkdayjobs.com",
    "icims.com",
    "paylocity.com",
]

def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()

def excluded(text):
    t = text.lower()
    return any(x in t for x in EXCLUDED)

def has_good_terms(text):
    t = text.lower()
    return any(x in t for x in GOOD_TERMS)

def has_bad_terms(text):
    t = text.lower()
    return any(x in t for x in BAD_TERMS)

def unwrap_duckduckgo(href):
    if not href:
        return ""
    if href.startswith("//"):
        return "https:" + href
    if "uddg=" in href:
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        if "uddg" in qs:
            return unquote(qs["uddg"][0])
    return href

def duckduckgo_search(query, max_results=10):
    url = "https://html.duckduckgo.com/html/"
    resp = requests.post(url, data={"q": query}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = []
    for block in soup.select(".result"):
        a = block.select_one(".result__title a")
        snippet_el = block.select_one(".result__snippet")
        if not a:
            continue

        title = clean(a.get_text(" ", strip=True))
        link = unwrap_duckduckgo(a.get("href", ""))
        snippet = clean(snippet_el.get_text(" ", strip=True) if snippet_el else "")
        domain = urlparse(link).netloc.lower()

        if not link:
            continue

        results.append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "domain": domain,
            "query": query
        })

        if len(results) >= max_results:
            break

    return results

def fetch_page_text(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = clean(soup.title.get_text()) if soup.title else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            meta_desc = clean(meta["content"])

        body_text = clean(" ".join(soup.stripped_strings))
        return {
            "title": title,
            "meta_desc": meta_desc,
            "body_text": body_text[:8000]
        }
    except Exception:
        return {
            "title": "",
            "meta_desc": "",
            "body_text": ""
        }

def extract_company(text):
    text = clean(text)

    patterns = [
        r"\b([A-Z][A-Za-z0-9&'’\-.]+(?:\s+[A-Z][A-Za-z0-9&'’\-.]+){0,4})\b"
    ]

    candidates = []
    for pattern in patterns:
        for match in re.findall(pattern, text):
            c = clean(match)
            if len(c) < 3:
                continue
            if c.lower() in {"ukg", "kronos", "linkedin", "indeed"}:
                continue
            if excluded(c):
                continue
            candidates.append(c)

    cleaned = []
    seen = set()
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(c)

    return cleaned[:10]

def score_result(title, snippet, page_title, meta_desc, body_text, domain):
    blob = " ".join([title, snippet, page_title, meta_desc, body_text[:2500], domain]).lower()
    score = 0

    if has_good_terms(blob):
        score += 4
    if has_bad_terms(blob):
        score -= 5
    if excluded(blob):
        score -= 10

    if any(d in domain for d in PUBLIC_DOMAINS_TO_PRIORITIZE):
        score += 2

    if "ukg" in blob or "kronos" in blob:
        score += 2

    if any(x in blob for x in ["implementation", "migration", "go live", "go-live", "rollout"]):
        score += 2

    return score

def classify_signal(text):
    t = text.lower()
    if "go live" in t or "go-live" in t:
        return "Go-live"
    if "migration" in t:
        return "Migration"
    if "rollout" in t:
        return "Rollout"
    if "upgrade" in t:
        return "Upgrade"
    if "implementation" in t:
        return "Implementation"
    if "replacement" in t or "replacing" in t:
        return "Replacement"
    if "selection" in t or "selecting" in t:
        return "Selection"
    if "transformation" in t:
        return "Transformation"
    return "Signal"

def summarize_text(title, snippet, meta_desc, body_text):
    pieces = [title, snippet, meta_desc]
    text = " | ".join([clean(x) for x in pieces if clean(x)])

    if len(text) < 80 and body_text:
        sents = re.split(r'(?<=[.!?])\s+', body_text)
        useful = []
        for s in sents:
            sl = s.lower()
            if "ukg" in sl or "kronos" in sl or any(x in sl for x in GOOD_TERMS):
                useful.append(clean(s))
            if len(" ".join(useful)) > 250:
                break
        if useful:
            text = " ".join(useful)

    return clean(text)[:350]

def build_digest():
    leads = {}

    for query in SEARCH_QUERIES:
        try:
            results = duckduckgo_search(query, max_results=8)
        except Exception as e:
            print(f"Search failed for {query}: {e}")
            continue

        for r in results:
            raw_blob = f"{r['title']} {r['snippet']} {r['link']}"
            if excluded(raw_blob):
                continue
            if not has_good_terms(raw_blob):
                continue

            page = fetch_page_text(r["link"])
            time.sleep(1.0)

            score = score_result(
                r["title"], r["snippet"], page["title"], page["meta_desc"], page["body_text"], r["domain"]
            )

            if score < 3:
                continue

            company_candidates = extract_company(
                " ".join([r["title"], r["snippet"], page["title"], page["meta_desc"]])
            )

            chosen_company = None
            for c in company_candidates:
                cl = c.lower()
                if excluded(cl):
                    continue
                if any(b in cl for b in ["implementation", "migration", "ukg", "kronos", "manager", "analyst", "consultant"]):
                    continue
                chosen_company = c
                break

            if not chosen_company:
                continue

            summary = summarize_text(r["title"], r["snippet"], page["meta_desc"], page["body_text"])
            signal = classify_signal(" ".join([r["title"], r["snippet"], page["meta_desc"], page["body_text"][:1000]]))

            key = chosen_company.lower()
            entry = leads.get(key)

            if entry is None or score > entry["score"]:
                leads[key] = {
                    "company": chosen_company,
                    "signal": signal,
                    "summary": summary,
                    "link": r["link"],
                    "domain": r["domain"],
                    "score": score
                }

    ranked = sorted(leads.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:20]

def email_digest(leads):
    if not leads:
        body = "No strong end-client UKG implementation or migration signals found today."
    else:
        body = "🔥 UKG END-CLIENT SIGNALS\n\n"
        for i, lead in enumerate(leads, 1):
            body += (
                f"{i}. {lead['company']}\n"
                f"Signal: {lead['signal']}\n"
                f"Why it matched: {lead['summary']}\n"
                f"Source: {lead['link']}\n\n"
            )

    msg = MIMEText(body)
    msg["Subject"] = "🔥 UKG End-Client Leads"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    leads = build_digest()
    email_digest(leads)
    print(f"Sent {len(leads)} leads")
