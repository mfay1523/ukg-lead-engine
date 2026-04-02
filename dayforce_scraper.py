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
    "Dayforce WFM",
    "Dayforce analyst",
    "Dayforce administrator",
    "Dayforce specialist",
    "Dayforce manager",
]

EXCLUDE_COMPANY_TERMS = [
    "accenture",
    "addison group",
    "allegis",
    "capgemini",
    "cognizant",
    "deloitte",
    "enforce consulting",
    "ey",
    "hcm unlocked",
    "hub international",
    "insight global",
    "infosys",
    "kapital data",
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
    "wise consulting",
    "wipro",
]

EXCLUDE_PUBLISHERS = [
    "career.com",
    "ihirehr",
    "jobilize",
    "jobrapido",
    "learn4good",
    "talents by vaia",
    "teal",
]

EXCLUDE_TEXT_TERMS = [
    "staffing",
    "recruiting",
    "recruiter",
    "consulting",
    "implementation consultant",
    "implementation partner",
    "managed services",
    "third party",
    "agency",
]

GOOD_TITLE_TERMS = [
    "dayforce",
    "ceridian",
    "payroll",
    "hris",
    "hcm",
    "wfm",
    "timekeeping",
    "administrator",
    "admin",
    "analyst",
    "specialist",
    "manager",
    "lead",
]

US_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
    "ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK",
    "OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
}


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


def looks_us_based(job):
    country = clean_text(job.get("job_country", ""))
    state = clean_text(job.get("job_state", "")).upper()
    city = clean_text(job.get("job_city", ""))
    location = clean_text(job.get("job_location", ""))

    if country.upper() in {"US", "USA", "UNITED STATES"}:
        return True
    if state in US_STATE_CODES:
        return True
    if "united states" in location.lower():
        return True
    if city and state in US_STATE_CODES:
        return True
    return False


def score_job(job):
    title = clean_text(job.get("title", "")).lower()
    description = clean_text(job.get("description", "")).lower()
    text = f"{title} {description}"

    score = 0

    if "dayforce" in text:
        score += 5
    if "ceridian" in text:
        score += 3
    if "payroll" in text:
        score += 2
    if "hris" in text:
        score += 2
    if "hcm" in text:
        score += 2
    if "wfm" in text:
        score += 2
    if "timekeeping" in text:
        score += 1
    if "administrator" in text or "admin" in text:
        score += 1
    if "analyst" in text:
        score += 1
    if "specialist" in text:
        score += 1
    if "manager" in text:
        score += 1
    if "lead" in text:
        score += 1

    return score


def is_excluded(job):
    employer = clean_text(job.get("company", "")).lower()
    title = clean_text(job.get("title", "")).lower()
    desc = clean_text(job.get("description", "")).lower()
    publisher = clean_text(job.get("publisher", "")).lower()

    blob = " ".join([employer, title, desc, publisher])

    if not employer or employer == "unknown company":
        return True
    if any(term in employer for term in EXCLUDE_COMPANY_TERMS):
        return True
    if any(term in publisher for term in EXCLUDE_PUBLISHERS):
        return True
    if any(term in blob for term in EXCLUDE_TEXT_TERMS):
        return True

    # exclude obvious Dayforce internal jobs
    if employer == "dayforce":
        return True

    return False


def title_is_relevant(title):
    title = clean_text(title).lower()
    return any(term in title for term in GOOD_TITLE_TERMS)


def fetch_jsearch_results():
    api_key = os.environ.get("JSEARCH_API_KEY")
    if not api_key:
        print("Missing JSEARCH_API_KEY")
        return []

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

            if response.status_code != 200:
                print(f"Response text for '{query}': {response.text[:500]}")
                continue

            payload = response.json()
            jobs = payload.get("data", [])
            print(f"Query '{query}' returned {len(jobs)} raw jobs")

            for job in jobs:
                if not looks_us_based(job):
                    continue

                employer = clean_text(job.get("job_employer_name", ""))
                title = clean_text(job.get("job_title", ""))
                city = clean_text(job.get("job_city", ""))
                state = clean_text(job.get("job_state", ""))
                location = clean_text(job.get("job_location", ""))
                publisher = clean_text(job.get("job_publisher", ""))
                description = clean_text(job.get("job_description", ""))
                link = clean_text(job.get("job_apply_link", "")) or clean_text(job.get("job_google_link", ""))

                display_location = ", ".join(x for x in [city, state] if x) or location or "Unknown"

                cleaned_job = {
                    "company": employer,
                    "title": title,
                    "location": display_location,
                    "publisher": publisher,
                    "link": link,
                    "description": description[:800],
                }

                if is_excluded(cleaned_job):
                    continue

                if not title_is_relevant(title) and "dayforce" not in description.lower() and "ceridian" not in description.lower():
                    continue

                cleaned_job["score"] = score_job(cleaned_job)
                all_jobs.append(cleaned_job)

        except Exception as e:
            print(f"JSearch request failed for '{query}': {e}")

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


def build_email_body(jobs):
    lines = []

    if not jobs:
        lines.append("No strong Dayforce hiring leads were found today.")
        return "\n".join(lines)

    jobs = sorted(jobs, key=lambda x: x.get("score", 0), reverse=True)

    lines.append("Strong Dayforce hiring leads:\n")

    for idx, job in enumerate(jobs, start=1):
        lines.append(f"{idx}. {job.get('company', 'Unknown Company')}")
        lines.append(f"   Title: {job.get('title', 'Unknown Title')}")
        lines.append(f"   Location: {job.get('location', 'Unknown')}")
        lines.append(f"   Source: {job.get('publisher', 'Unknown')}")
        lines.append(f"   Score: {job.get('score', 0)}")
        if job.get("link"):
            lines.append(f"   Link: {job['link']}")
        if job.get("description"):
            lines.append(f"   Summary: {job['description'][:250]}")
        lines.append("")

    return "\n".join(lines)


def send_email(subject, body):
    email_user = os.environ.get("EMAIL_ADDRESS")
    email_pass = os.environ.get("EMAIL_APP_PASSWORD")
    alert_to = os.environ.get("EMAIL_ADDRESS")

    if not email_user or not email_pass or not alert_to:
        print("Missing EMAIL_ADDRESS or EMAIL_APP_PASSWORD")
        print(body)
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = email_user
        msg["To"] = alert_to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.sendmail(email_user, [alert_to], msg.as_string())

        print("Email sent successfully")
    except Exception as e:
        print(f"Email send failed: {e}")


def main():
    print("Fetching JSearch Dayforce jobs...")
    jobs = fetch_jsearch_results()
    print(f"Raw filtered jobs: {len(jobs)}")

    jobs = dedupe_jobs(jobs)
    print(f"After dedupe: {len(jobs)}")

    seen_links = load_seen_links()
    new_jobs = []

    for job in jobs:
        link = clean_text(job.get("link", ""))
        dedupe_key = link or f"{job['company']}|{job['title']}|{job['location']}"
        if dedupe_key not in seen_links:
            new_jobs.append(job)
            seen_links.add(dedupe_key)

    save_seen_links(seen_links)
    print(f"New jobs: {len(new_jobs)}")

    subject = f"Dayforce Hiring Leads: {len(new_jobs)}"
    body = build_email_body(new_jobs[:25])
    send_email(subject, body)
    print(body)


if __name__ == "__main__":
    main()
