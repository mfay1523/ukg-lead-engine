import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urljoin

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

HEADERS = {"User-Agent": USER_AGENT}
SEEN_FILE = "seen_jobs_dayforce.json"
MIN_SCORE = 1
REQUEST_TIMEOUT = 20

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

KEYWORDS = [
    "dayforce",
    "ceridian",
    "ceridian dayforce",
    "dayforce hcm",
    "dayforce payroll",
    "dayforce wfm",
    "dayforce time",
    "dayforce hris",
    "dayforce analyst",
    "dayforce administrator",
    "dayforce specialist",
    "dayforce consultant",
    "dayforce support",
    "dayforce manager",
]

# Replace these with companies you actually want to monitor.
GREENHOUSE_BOARDS = [
    "https://boards.greenhouse.io/embed/job_board?for=hubspot",
    "https://boards.greenhouse.io/embed/job_board?for=doordash",
    "https://boards.greenhouse.io/embed/job_board?for=datadog",
    "https://boards.greenhouse.io/embed/job_board?for=affirm",
    "https://boards.greenhouse.io/embed/job_board?for=coinbase",
    "https://boards.greenhouse.io/embed/job_board?for=robinhood",
    "https://boards.greenhouse.io/embed/job_board?for=brex",
    "https://boards.greenhouse.io/embed/job_board?for=stripe",
]

LEVER_BOARDS = [
    "https://jobs.lever.co/figma",
    "https://jobs.lever.co/notion",
    "https://jobs.lever.co/ramp",
    "https://jobs.lever.co/chime",
    "https://jobs.lever.co/discord",
    "https://jobs.lever.co/mongodb",
]


def clean_text(value):
    return " ".join((value or "").split()).strip()


def load_seen_links():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data if isinstance(data, list) else [])
    except Exception as e:
        print(f"Could not read {SEEN_FILE}: {e}")
        return set()


def save_seen_links(links):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(links)), f, indent=2)
    except Exception as e:
        print(f"Could not save {SEEN_FILE}: {e}")


def fetch_soup(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"Request failed for {url}: {e}")
        return None


def is_excluded_company(job):
    company = clean_text(job.get("company", "")).lower()
    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
        job.get("description", ""),
        job.get("link", ""),
    ]).lower()

    for bad in EXCLUDE_COMPANIES:
        if bad in company or bad in text:
            return True
    return False


def score_job(job):
    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
        job.get("description", ""),
        job.get("link", ""),
    ]).lower()

    score = 0

    if "dayforce" in text:
        score += 5
    if "ceridian" in text:
        score += 3
    if "payroll" in text:
        score += 1
    if "hris" in text:
        score += 1
    if "hcm" in text:
        score += 1
    if "wfm" in text:
        score += 1
    if "time" in text or "timekeeping" in text:
        score += 1
    if "administrator" in text:
        score += 1
    if "analyst" in text:
        score += 1
    if "specialist" in text:
        score += 1
    if "manager" in text:
        score += 1
    if "support" in text:
        score += 1
    if "consultant" in text:
        score += 1

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


def has_dayforce_keyword(text):
    text = (text or "").lower()
    return any(keyword in text for keyword in KEYWORDS)


def is_relevant(job):
    if is_excluded_company(job):
        return False

    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
        job.get("description", ""),
        job.get("link", ""),
    ]).lower()

    if not has_dayforce_keyword(text):
        return False

    job["score"] = score_job(job)
    return job["score"] >= MIN_SCORE


def extract_greenhouse_job_links(board_url):
    jobs = []
    soup = fetch_soup(board_url)
    if not soup:
        return jobs

    for a in soup.select("a[href]"):
        title = clean_text(a.get_text(" ", strip=True))
        href = a.get("href", "")
        if not title or not href:
            continue

        if "/jobs/" not in href and "gh_jid" not in href:
            continue

        full_link = urljoin("https://boards.greenhouse.io", href)
        company = board_url.split("for=")[-1]

        location = ""
        parent = a.parent
        if parent:
            text = clean_text(parent.get_text(" ", strip=True))
            if text and text != title:
                location = text.replace(title, "").strip(" -|,")

        jobs.append({
            "title": title[:180],
            "company": company,
            "location": location[:120],
            "summary": title[:400],
            "link": full_link,
            "source": "Greenhouse",
        })

    return jobs


def extract_lever_job_links(board_url):
    jobs = []
    soup = fetch_soup(board_url)
    if not soup:
        return jobs

    for a in soup.select("a[href]"):
        title = clean_text(a.get_text(" ", strip=True))
        href = a.get("href", "")
        if not title or not href:
            continue

        if "/jobs.lever.co/" not in href and "/lever.co/" not in href and not href.startswith("/"):
            continue

        full_link = urljoin(board_url.rstrip("/") + "/", href)
        company = board_url.rstrip("/").split("/")[-1]

        jobs.append({
            "title": title[:180],
            "company": company,
            "location": "",
            "summary": title[:400],
            "link": full_link,
            "source": "Lever",
        })

    return jobs


def enrich_job_with_description(job):
    soup = fetch_soup(job["link"])
    if not soup:
        job["description"] = ""
        return job

    text = clean_text(soup.get_text(" ", strip=True))
    job["description"] = text[:12000]

    if not job.get("location"):
        location_selectors = [
            ".location",
            ".job__location",
            ".posting-categories .location",
            "[data-qa='posting-location']",
        ]
        for selector in location_selectors:
            loc_el = soup.select_one(selector)
            if loc_el:
                job["location"] = clean_text(loc_el.get_text(" ", strip=True))[:120]
                break

    return job


def fetch_greenhouse_results():
    listing_jobs = []
    enriched_jobs = []

    for board_url in GREENHOUSE_BOARDS:
        listing_jobs.extend(extract_greenhouse_job_links(board_url))

    print(f"Greenhouse listing jobs found: {len(listing_jobs)}")

    for job in listing_jobs:
        enriched = enrich_job_with_description(job)
        if is_relevant(enriched):
            enriched_jobs.append(enriched)

    return enriched_jobs


def fetch_lever_results():
    listing_jobs = []
    enriched_jobs = []

    for board_url in LEVER_BOARDS:
        listing_jobs.extend(extract_lever_job_links(board_url))

    print(f"Lever listing jobs found: {len(listing_jobs)}")

    for job in listing_jobs:
        enriched = enrich_job_with_description(job)
        if is_relevant(enriched):
            enriched_jobs.append(enriched)

    return enriched_jobs


def build_email_body(jobs, debug_summary):
    lines = [debug_summary, ""]

    if not jobs:
        lines.append("No new Dayforce leads were found today.")
        return "\n".join(lines)

    lines.append("New Dayforce leads found:\n")

    for i, job in enumerate(jobs, start=1):
        lines.append(f"{i}. {job.get('title', 'No title')}")
        lines.append(f"   Company: {job.get('company', 'Unknown') or 'Unknown'}")
        lines.append(f"   Location: {job.get('location', 'Unknown') or 'Unknown'}")
        lines.append(f"   Source: {job.get('source', 'Unknown')}")
        lines.append(f"   Score: {job.get('score', 0)}")
        lines.append(f"   Link: {job.get('link', '')}")
        desc = clean_text(job.get("description", ""))[:250]
        lines.append(f"   Summary: {desc}")
        lines.append("")

    return "\n".join(lines)


def send_email(subject, body):
    try:
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

        print("Email sent successfully.")
    except Exception as e:
        print(f"Email send failed: {e}")


def main():
    all_jobs = []

    print("Fetching Greenhouse results...")
    greenhouse_jobs = fetch_greenhouse_results()
    print(f"Greenhouse relevant jobs found: {len(greenhouse_jobs)}")
    all_jobs.extend(greenhouse_jobs)

    print("Fetching Lever results...")
    lever_jobs = fetch_lever_results()
    print(f"Lever relevant jobs found: {len(lever_jobs)}")
    all_jobs.extend(lever_jobs)

    print(f"Raw results before dedupe: {len(all_jobs)}")

    all_jobs = dedupe_jobs(all_jobs)
    print(f"After dedupe: {len(all_jobs)}")

    all_jobs = sorted(all_jobs, key=lambda x: x.get("score", 0), reverse=True)
    print(f"Relevant jobs after dedupe: {len(all_jobs)}")

    seen_links = load_seen_links()
    new_jobs = []

    for job in all_jobs:
        link = clean_text(job.get("link", ""))
        if link and link not in seen_links:
            new_jobs.append(job)
            seen_links.add(link)

    save_seen_links(seen_links)
    print(f"New jobs: {len(new_jobs)}")

    debug_summary = (
        f"Greenhouse relevant jobs found: {len(greenhouse_jobs)}\n"
        f"Lever relevant jobs found: {len(lever_jobs)}\n"
        f"Raw results after dedupe: {len(all_jobs)}\n"
        f"New jobs: {len(new_jobs)}"
    )

    subject = f"Dayforce Leads: {len(new_jobs)} new matches"
    body = build_email_body(new_jobs[:25], debug_summary)

    send_email(subject, body)
    print(body)


if __name__ == "__main__":
    main()
