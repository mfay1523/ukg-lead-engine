import os
import json
import smtplib
import requests
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SEEN_FILE = "seen_jobs_dayforce.json"

EXCLUDE_COMPANIES = [
    "rsm","pwc","hub international","marsh","red pill labs",
    "enforce consulting","seequelle","providence technology services",
    "silver cloud","axl global consulting","allegis","teksystems",
    "insight global","randstad","kforce","robert half",
    "deloitte","accenture","kpmg","ey"
]

KEYWORDS = [
    "dayforce",
    "ceridian",
    "ceridian dayforce"
]

SEARCH_QUERIES = [
    "dayforce jobs",
    "ceridian dayforce jobs",
    "dayforce payroll",
    "dayforce hcm",
    "dayforce wfm",
    "dayforce analyst",
    "dayforce administrator",
    "dayforce specialist",
]

def load_seen_links():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(json.load(f))

def save_seen_links(links):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(links), f, indent=2)

def is_excluded(text):
    text = text.lower()
    return any(bad in text for bad in EXCLUDE_COMPANIES)

def fetch_google_rss():
    results = []

    for query in SEARCH_QUERIES:
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
        try:
            response = requests.get(url, timeout=15)
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = item.find("title").text or ""
                link = item.find("link").text or ""

                text = f"{title} {link}".lower()

                if not any(k in text for k in KEYWORDS):
                    continue

                if is_excluded(text):
                    continue

                results.append({
                    "title": title,
                    "link": link,
                    "source": "Google RSS"
                })

        except Exception as e:
            print("RSS error:", e)

    return results

def dedupe(jobs):
    seen = set()
    output = []
    for j in jobs:
        if j["link"] not in seen:
            seen.add(j["link"])
            output.append(j)
    return output

def send_email(subject, body):
    email_user = os.environ["EMAIL_ADDRESS"]
    email_pass = os.environ["EMAIL_APP_PASSWORD"]

    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = email_user
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(email_user, email_pass)
        server.sendmail(email_user, [email_user], msg.as_string())

def build_body(jobs):
    if not jobs:
        return "No Dayforce leads found."

    lines = ["Dayforce Leads:\n"]
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['title']}")
        lines.append(f"   {j['link']}")
        lines.append("")

    return "\n".join(lines)

def main():
    print("Fetching RSS results...")
    jobs = fetch_google_rss()

    print(f"Raw results: {len(jobs)}")

    jobs = dedupe(jobs)

    seen = load_seen_links()
    new_jobs = []

    for j in jobs:
        if j["link"] not in seen:
            new_jobs.append(j)
            seen.add(j["link"])

    save_seen_links(seen)

    print(f"New jobs: {len(new_jobs)}")

    subject = f"Dayforce Leads: {len(new_jobs)}"
    body = build_body(new_jobs[:20])

    send_email(subject, body)

if __name__ == "__main__":
    main()
