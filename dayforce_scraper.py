import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SEEN_FILE = "seen_jobs_dayforce.json"

RAPIDAPI_HOST = "jsearch.p.rapidapi.com"
RAPIDAPI_URL = "https://jsearch.p.rapidapi.com/search"

SEARCH_QUERIES = [
    "Dayforce",
    "Ceridian",
    "Dayforce payroll",
    "Dayforce HRIS",
    "Dayforce HCM",
]

EXCLUDE_COMPANY_TERMS = [
    "accenture",
    "allegis",
    "capgemini",
    "cognizant",
    "deloitte",
    "enforce consulting",
    "ey",
    "hub international",
    "insight global",
    "infosys",
    "kforce",
    "kpmg",
    "marsh",
    "pwc",
    "randstad",
    "red pill labs",
    "robert half",
    "rsm",
    "seequelle",
    "silver cloud",
    "teksystems",
    "wipro",
]

EXCLUDE_TEXT_TERMS = [
    "staffing",
    "recruiting",
    "recruiter",
    "consulting",
    "consultant firm",
    "partner",
    "implementation partner",
    "managed services",
    "third party",
    "agency",
]


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


def clean_text(value):
    return " ".join((value or "").split()).strip()


def is_excluded(job):
    employer = clean_text(job.get("job_employer_name", "")).lower()
    title = clean_text(job.get("job_title", "")).lower()
    desc = clean_text(job.get("job_description", "")).lower()
    publisher = clean_text(job.get("job_publisher", "")).lower()

    blob = " ".join([employer, title, desc, publisher])

    if any(term in employer for term in EXCLUDE_COMPANY_TERMS):
        return True
    if any(term in blob for term in EXCLUDE_TEXT_TERMS):
        return True
    return False


def fetch_jsearch_results():
    api_key = os.environ["JSEARCH_API_KEY"]

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }

    all_jobs = []

    for query in SEARCH_QUERIES:
        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "country": "us",
            "date_posted": "all",
        }

        try:
            response = requests.get(RAPIDAPI_URL, headers=headers, params=params, timeout=30)
            print(f"Query '{query}' status: {response.status_code}")
            response.raise_for_status()

            payload = response.json()
            print(f"Query '{query}' raw payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'not a dict'}")

            jobs = payload.get("data", []) if isinstance(payload, dict) else []
            print(f"Query '{query}' returned {len(jobs)} raw jobs from API")

            for job in jobs:
                employer = clean_text(job.get("job_employer_name", "Unknown Company"))
                title = clean_text(job.get("job_title", "Unknown Title"))
                city = clean_text(job.get("job_city", ""))
                state = clean_text(job.get("job_state", ""))
                location = clean_text(job.get("job_location", ""))
                publisher = clean_text(job.get("job_publisher", ""))
                description = clean_text(job.get("job_description", ""))
                apply_link = clean_text(job.get("job_apply_link", ""))
                google_link = clean_text(job.get("job_google_link", ""))

                link = apply_link or google_link
                display_location = ", ".join(x for x in [city, state] if x) or location or "Unknown"

                cleaned_job = {
                    "company": employer,
                    "title": title,
                    "location": display_location,
                    "publisher": publisher,
                    "link": link,
                    "description": description[:600],
                    "raw_text": f"{employer} {title} {location} {publisher} {description}".lower(),
                }

                all_jobs.append(cleaned_job)

        except Exception as e:
            print(f"JSearch failed for query '{query}': {e}")

    return all_jobs


def dedupe_jobs(jobs):
    seen = set()
    output = []

    for job in jobs:
        key = (
            clean_text(job.get("company", "")).lower(),
            clean_text(job.get("title", "")).lower(),
            clean_text(job.get("location", "")).lower(),
            clean_text(job.get("link", "")).lower(),
        )
        if key not in seen:
            seen.add(key)
            output.append(job)

    return output


def build_email_body(jobs, raw_count, deduped_count):
    lines = [
        f"Raw jobs from API: {raw_count}",
        f"After dedupe: {deduped_count}",
        f"Final jobs emailed: {len(jobs)}",
        "",
    ]

    if not jobs:
        lines.append("No Dayforce hiring activity found.")
        return "\n".join(lines)

    lines.append("Dayforce hiring activity:\n")

    for idx, job in enumerate(jobs, start=1):
        lines.append(f"{idx}. {job.get('company', 'Unknown Company')}")
        lines.append(f"   Title: {job.get('title', 'Unknown Title')}")
        lines.append(f"   Location: {job.get('location', 'Unknown')}")
        lines.append(f"   Source: {job.get('publisher', 'Unknown')}")
        if job.get("link"):
            lines.append(f"   Link: {job['link']}")
        if job.get("description"):
            lines.append(f"   Summary: {job['description'][:250]}")
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


def main():
    print("Fetching JSearch Dayforce jobs...")
    jobs = fetch_jsearch_results()
    raw_count = len(jobs)
    print(f"Raw jobs from API: {raw_count}")

    if jobs:
        print("Sample jobs:")
        for job in jobs[:5]:
            print(job)

    jobs = dedupe_jobs(jobs)
    deduped_count = len(jobs)
    print(f"After dedupe: {deduped_count}")

    # TEMP: leave filtering very loose so we can prove the API is returning data
    filtered_jobs = []
    for job in jobs:
        text = job.get("raw_text", "")
        if ("dayforce" in text or "ceridian" in text) and not is_excluded({
            "job_employer_name": job.get("company", ""),
            "job_title": job.get("title", ""),
            "job_description": job.get("description", ""),
            "job_publisher": job.get("publisher", ""),
        }):
            filtered_jobs.append(job)

    print(f"After loose filtering: {len(filtered_jobs)}")

    seen_links = load_seen_links()
    new_jobs = []

    for job in filtered_jobs:
        link = clean_text(job.get("link", ""))
        dedupe_key = link or f"{job['company']}|{job['title']}|{job['location']}"
        if dedupe_key not in seen_links:
            new_jobs.append(job)
            seen_links.add(dedupe_key)

    save_seen_links(seen_links)
    print(f"New jobs: {len(new_jobs)}")

    subject = f"Dayforce Hiring Leads: {len(new_jobs)}"
    body = build_email_body(new_jobs[:25], raw_count, deduped_count)
    send_email(subject, body)
    print(body)


if __name__ == "__main__":
    main()
