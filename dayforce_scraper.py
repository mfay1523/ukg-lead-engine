import os
import json
import smtplib
import requests
from urllib.parse import urlparse
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
    "Dayforce consultant",
    "Dayforce implementation",
    "Dayforce integration",
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
    "dayforce",
]

BAD_DOMAINS = [
    "career.com",
    "ihirehr.com",
    "jobilize.com",
    "jobrapido.com",
    "jooble.org",
    "learn4good.com",
    "lensa.com",
    "recruit.net",
    "talents.vaia.com",
    "vaia.com",
    "tealhq.com",
    "ziprecruiter.com",
]

EXCLUDE_TEXT_TERMS = [
    "staffing",
    "recruiting",
    "recruiter",
    "third party",
    "agency",
]

GOOD_TEXT_TERMS = [
    "dayforce",
    "ceridian",
    "payroll",
    "hris",
    "hcm",
    "wfm",
    "timekeeping",
]

US_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
    "ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK",
    "OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
}


def clean_text(value):
    return " ".join((value or "").split()).strip()


def extract_domain(link):
    try:
        netloc = urlparse(link).netloc.lower()
        return netloc.replace("www.", "")
    except:
        return ""


def is_bad_domain(link):
    domain = extract_domain(link)
    return any(bad in domain for bad in BAD_DOMAINS)


def domain_to_company(link):
    domain = extract_domain(link)
    if not domain:
        return ""

    parts = domain.split(".")
    base = parts[-2] if len(parts) >= 2 else domain
    base = base.replace("-", " ").replace("_", " ")

    return " ".join(word.capitalize() for word in base.split())


def normalize_company(company, link):
    company = clean_text(company)

    if company and company.lower() != "unknown company":
        return company

    if is_bad_domain(link):
        return company

    return domain_to_company(link)


def looks_us_based(job):
    country = clean_text(job.get("job_country", ""))
    state = clean_text(job.get("job_state", "")).upper()

    if country.upper() in {"US", "USA", "UNITED STATES"}:
        return True
    if state in US_STATE_CODES:
        return True

    return False


def is_excluded(job):
    employer = job["company"].lower()
    text = f"{job['title']} {job['description']}".lower()

    if not employer or employer == "unknown company":
        return True
    if any(term in employer for term in EXCLUDE_COMPANY_TERMS):
        return True
    if is_bad_domain(job["link"]):
        return True
    if any(term in text for term in EXCLUDE_TEXT_TERMS):
        return True

    return False


def is_relevant(job):
    text = f"{job['title']} {job['description']} {job['company']}".lower()
    return any(term in text for term in GOOD_TEXT_TERMS)


def score_job(job):
    text = f"{job['title']} {job['description']}".lower()

    score = 0
    if "dayforce" in text: score += 5
    if "ceridian" in text: score += 3
    if "payroll" in text: score += 2
    if "hris" in text: score += 2
    if "hcm" in text: score += 2
    if "wfm" in text: score += 2
    if "implementation" in text: score += 2
    if "integration" in text: score += 2
    if "consultant" in text: score += 1
    if "analyst" in text: score += 1

    return score


def fetch_jobs():
    api_key = os.environ["JSEARCH_API_KEY"]

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }

    results = []

    for query in SEARCH_QUERIES:
        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "country": "us",
        }

        res = requests.get(RAPIDAPI_URL, headers=headers, params=params)
        data = res.json().get("data", [])

        for j in data:
            if not looks_us_based(j):
                continue

            link = j.get("job_apply_link") or j.get("job_google_link") or ""
            company = normalize_company(j.get("job_employer_name", ""), link)

            job = {
                "company": company,
                "title": clean_text(j.get("job_title")),
                "location": clean_text(j.get("job_location")),
                "link": link,
                "description": clean_text(j.get("job_description", ""))[:500],
            }

            if not is_relevant(job):
                continue
            if is_excluded(job):
                continue

            job["score"] = score_job(job)
            results.append(job)

    return results


def dedupe(jobs):
    seen = set()
    out = []

    for j in jobs:
        key = f"{j['company']}|{j['title']}|{j['location']}"
        if key not in seen:
            seen.add(key)
            out.append(j)

    return out


def send_email(subject, body):
    email = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_APP_PASSWORD"]

    msg = MIMEMultipart()
    msg["From"] = email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(email, password)
        s.sendmail(email, [email], msg.as_string())


def main():
    jobs = fetch_jobs()
    jobs = dedupe(jobs)

    if not jobs:
        send_email("Dayforce Leads: 0", "No Dayforce hiring leads found.")
        return

    jobs = sorted(jobs, key=lambda x: x["score"], reverse=True)

    lines = ["Dayforce hiring leads:\n"]

    for j in jobs[:20]:
        lines.append(f"{j['company']}")
        lines.append(f"  {j['title']}")
        lines.append(f"  {j['location']}")
        lines.append(f"  Score: {j['score']}")
        lines.append(f"  {j['link']}")
        lines.append("")

    send_email(f"Dayforce Leads: {len(jobs)}", "\n".join(lines))


if __name__ == "__main__":
    main()
