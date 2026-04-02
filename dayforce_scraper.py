import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote_plus

# =========================
# CONFIG
# =========================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

SEEN_FILE = "seen_jobs_dayforce.json"
MIN_SCORE = 6

KEYWORDS = [
    "dayforce",
    "ceridian dayforce",
    "dayforce hcm",
    "dayforce payroll",
    "dayforce wfm",
    "dayforce implementation",
    "dayforce migration",
    "dayforce consultant",
    "dayforce integration",
    "dayforce go-live",
    "dayforce cutover",
]

HIGH_INTENT_TERMS = [
    "implementation",
    "migrate",
    "migration",
    "rollout",
    "deploy",
    "deployment",
    "go-live",
    "cutover",
    "configuration",
    "integrations",
    "integration",
    "interface",
    "api",
    "payroll",
    "timekeeping",
    "wfm",
    "hcm",
    "hris",
    "enterprise applications",
]

END_CLIENT_TERMS = [
    "internal hris",
    "internal payroll",
    "in-house",
    "corporate hr",
    "enterprise applications",
    "hr systems",
    "payroll systems",
    "manager, hris",
    "director, payroll",
    "hr technology",
]

EXCLUDE_TERMS = [
    "partner",
    "dayforce partner",
    "services delivery partner",
    "consulting partner",
    "implementation partner",
    "technology partner",
    "broker partner",
    "software partner",
    "system integrator",
    "systems integrator",
    "managed services",
    "staffing firm",
    "recruiting firm",
    "third party",
    "vendor partner",
    "reseller",
]

EXCLUDE_COMPANIES = [
    "rsm",
    "pwc",
    "hub international",
    "marsh",
    "red pill labs",
    "enforce consulting",
    "seequelle",
    "providence technology services",
    "silver cloud",
    "axl global consulting",
    "allegis",
    "teksystems",
    "insight global",
    "randstad",
    "kforce",
    "robert half",
    "deloitte",
    "accenture",
    "kpmg",
    "ey",
]

SEARCH_QUERIES = [
    "Dayforce implementation jobs",
    "Dayforce migration jobs",
    "Dayforce payroll jobs",
    "Dayforce WFM jobs",
    "Dayforce integration jobs",
    "Dayforce HRIS jobs",
]

# =========================
# HELPERS
# =========================

def load_seen_links():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen_links(links):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(links)), f, indent=2)


def clean_text(value):
    return " ".join((value or "").split()).strip()


def is_partner_or_excluded(job):
    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
    ]).lower()

    company = (job.get("company", "") or "").lower()

    for term in EXCLUDE_TERMS:
        if term in text:
            return True

    for bad in EXCLUDE_COMPANIES:
        if bad in company:
            return True

    return False


def score_job(job):
    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
    ]).lower()

    score = 0

    if "dayforce" in text:
        score += 5

    if "ceridian dayforce" in text:
        score += 2

    for term in HIGH_INTENT_TERMS:
        if term in text:
            score += 2

    for term in END_CLIENT_TERMS:
        if term in text:
            score += 3

    for term in ["integration", "integrations", "interface", "api", "studio"]:
        if term in text:
            score += 1

    for term in EXCLUDE_TERMS:
        if term in text:
            score -= 8

    company = (job.get("company", "") or "").lower()
    for bad in EXCLUDE_COMPANIES:
        if bad in company:
            score -= 15

    return score


def dedupe_jobs(jobs):
    seen = set()
    output = []

    for job in jobs:
        key = (
            clean_text(job.get("title", "")).lower(),
            clean_text(job.get("company", "")).lower(),
            clean_text(job.get("link", "")).lower(),
        )
        if key not in seen:
            seen.add(key)
            output.append(job)

    return output


def is_relevant(job):
    if is_partner_or_excluded(job):
        return False

    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
    ]).lower()

    if "dayforce" not in text:
        return False

    job["score"] = score_job(job)
    return job["score"] >= MIN_SCORE


# =========================
# SOURCES
# =========================

def fetch_google_results():
    results = []
    headers = {"User-Agent": USER_AGENT}

    for query in SEARCH_QUERIES:
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select("a[href]"):
                href = a.get("href", "")
                text = clean_text(a.get_text(" ", strip=True))

                if not text:
                    continue

                lower_blob = f"{text} {href}".lower()
                if "dayforce" not in lower_blob:
                    continue

                if href.startswith("/url?q="):
                    href = href.split("/url?q=")[-1].split("&")[0]

                if not href.startswith("http"):
                    continue

                results.append({
                    "title": text[:180],
                    "company": "",
                    "location": "",
                    "summary": text[:400],
                    "link": href,
                    "source": "Google",
                })
        except Exception as e:
            print(f"Google search failed for '{query}': {e}")

    return results


def fetch_indeed_results():
    results = []
    headers = {"User-Agent": USER_AGENT}
    url = "https://www.indeed.com/jobs?q=Dayforce"

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("a[href]"):
            text = clean_text(a.get_text(" ", strip=True))
            href = a.get("href", "")

            if "dayforce" not in f"{text} {href}".lower():
                continue

            if href.startswith("/"):
                href = f"https://www.indeed.com{href}"

            if not href.startswith("http"):
                continue

            results.append({
                "title": text[:180] or "Dayforce role",
                "company": "",
                "location": "",
                "summary": text[:400],
                "link": href,
                "source": "Indeed",
            })
    except Exception as e:
        print(f"Indeed search failed: {e}")

    return results


# =========================
# EMAIL
# =========================

def build_email_body(jobs):
    if not jobs:
        return "No new Dayforce leads were found today."

    lines = []
    lines.append("New Dayforce leads found:\n")

    for i, job in enumerate(jobs, start=1):
        lines.append(f"{i}. {job.get('title', 'No title')}")
        lines.append(f"   Company: {job.get('company', 'Unknown') or 'Unknown'}")
        lines.append(f"   Location: {job.get('location', 'Unknown') or 'Unknown'}")
        lines.append(f"   Source: {job.get('source', 'Unknown')}")
        lines.append(f"   Score: {job.get('score', 0)}")
        lines.append(f"   Link: {job.get('link', '')}")
        lines.append(f"   Summary: {job.get('summary', '')[:250]}")
        lines.append("")

    return "\n".join(lines)


def send_email(subject, body):
    email_user = os.environ["EMAIL_ADDRESS"]
    email_pass = os.environ["EMAIL_APP_PASSWORD"]
    alert_to = os.environ["EMAIL_ADDRESS"]

    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = alert_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(email_user, email_pass)
        server.sendmail(email_user, [alert_to], msg.as_string())


# =========================
# MAIN
# =========================

def main():
    all_jobs = []

    print("Fetching Google results...")
    all_jobs.extend(fetch_google_results())

    print("Fetching Indeed results...")
    all_jobs.extend(fetch_indeed_results())

    print(f"Raw results: {len(all_jobs)}")

    all_jobs = dedupe_jobs(all_jobs)
    print(f"After dedupe: {len(all_jobs)}")

    relevant_jobs = [job for job in all_jobs if is_relevant(job)]
    relevant_jobs = sorted(relevant_jobs, key=lambda x: x.get("score", 0), reverse=True)

    print(f"Relevant jobs: {len(relevant_jobs)}")

    seen_links = load_seen_links()
    new_jobs = []

    for job in relevant_jobs:
        link = clean_text(job.get("link", ""))
        if link and link not in seen_links:
            new_jobs.append(job)
            seen_links.add(link)

    save_seen_links(seen_links)

    print(f"New jobs: {len(new_jobs)}")

    subject = f"Dayforce Leads: {len(new_jobs)} new matches"
    body = build_email_body(new_jobs[:25])

    send_email(subject, body)
    print(body)


if __name__ == "__main__":
    main()
