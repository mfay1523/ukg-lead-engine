import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

SEEN_FILE = "seen_jobs_dayforce.json"
MIN_SCORE = 1

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

# Much looser keyword list
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

# Broader boards to scan
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

def load_seen_links():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data if isinstance(data, list) else [])
    except Exception:
        return set()

def save_seen_links(links):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(links)), f, indent=2)
    except Exception as e:
        print(f"Could not save seen links: {e}")

def clean_text(value):
    return " ".join((value or "").split()).strip()

def is_excluded_company(job):
    company = clean_text(job.get("company", "")).lower()
    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
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
    if "time" in text:
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

def is_relevant(job):
    if is_excluded_company(job):
        return False

    text = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("summary", ""),
        job.get("location", ""),
        job.get("link", ""),
    ]).lower()

    if not any(keyword in text for keyword in KEYWORDS):
        return False

    job["score"] = score_job(job)
    return job["score"] >= MIN_SCORE

def fetch_greenhouse_results():
    results = []
    headers = {"User-Agent": USER_AGENT}

    for url in GREENHOUSE_BOARDS:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select("a[href]"):
                title = clean_text(a.get_text(" ", strip=True))
                href = a.get("href", "")

                if not title:
                    continue

                blob = f"{title} {href}".lower()
                if not any(keyword in blob for keyword in KEYWORDS):
                    continue

                if href.startswith("/"):
                    href = "https://boards.greenhouse.io" + href

                results.append({
                    "title": title[:180],
                    "company": url.split("for=")[-1],
                    "location": "",
                    "summary": title[:400],
                    "link": href,
                    "source": "Greenhouse",
                })
        except Exception as e:
            print(f"Greenhouse failed for {url}: {e}")

    return results

def fetch_lever_results():
    results = []
    headers = {"User-Agent": USER_AGENT}

    for url in LEVER_BOARDS:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for a in soup.select("a[href]"):
                title = clean_text(a.get_text(" ", strip=True))
                href = a.get("href", "")

                if not title:
                    continue

                blob = f"{title} {href}".lower()
                if not any(keyword in blob for keyword in KEYWORDS):
                    continue

                if href.startswith("/"):
                    href = url.rstrip("/") + href

                results.append({
                    "title": title[:180],
                    "company": url.split("/")[-1],
                    "location": "",
                    "summary": title[:400],
                    "link": href,
                    "source": "Lever",
                })
        except Exception as e:
            print(f"Lever failed for {url}: {e}")

    return results

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
        lines.append(f"   Summary: {job.get('summary', '')[:250]}")
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
    print(f"Greenhouse results found: {len(greenhouse_jobs)}")
    all_jobs.extend(greenhouse_jobs)

    print("Fetching Lever results...")
    lever_jobs = fetch_lever_results()
    print(f"Lever results found: {len(lever_jobs)}")
    all_jobs.extend(lever_jobs)

    print(f"Raw results before dedupe: {len(all_jobs)}")

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

    debug_summary = (
        f"Greenhouse results found: {len(greenhouse_jobs)}\n"
        f"Lever results found: {len(lever_jobs)}\n"
        f"Raw results after dedupe: {len(all_jobs)}\n"
        f"Relevant jobs: {len(relevant_jobs)}\n"
        f"New jobs: {len(new_jobs)}"
    )

    subject = f"Dayforce Leads: {len(new_jobs)} new matches"
    body = build_email_body(new_jobs[:25], debug_summary)

    send_email(subject, body)
    print(body)

if __name__ == "__main__":
    main()
