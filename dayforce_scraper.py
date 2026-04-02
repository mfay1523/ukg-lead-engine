import os
import json
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

HEADERS = {"User-Agent": "Mozilla/5.0"}
SEEN_FILE = "seen_jobs_dayforce.json"

EXCLUDE_TERMS = [
    "consulting", "staffing", "recruiting", "agency",
    "partner", "solutions", "services", "llc"
]

KEYWORDS = ["dayforce", "ceridian"]

SEARCH_URLS = [
    "https://www.indeed.com/jobs?q=dayforce&l=United+States",
    "https://www.indeed.com/jobs?q=ceridian&l=United+States"
]

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(json.load(open(SEEN_FILE)))

def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))

def is_valid_company(company):
    c = company.lower()
    return not any(term in c for term in EXCLUDE_TERMS)

def fetch_jobs():
    jobs = []

    for url in SEARCH_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")

            for card in soup.select("a[href]"):
                text = card.get_text(" ", strip=True)

                if not text:
                    continue

                blob = text.lower()

                if not any(k in blob for k in KEYWORDS):
                    continue

                href = card.get("href")
                if not href:
                    continue

                if href.startswith("/"):
                    href = "https://www.indeed.com" + href

                jobs.append({
                    "title": text[:150],
                    "company": "",
                    "link": href
                })

        except Exception as e:
            print("Error:", e)

    return jobs

def dedupe(jobs):
    seen = set()
    out = []
    for j in jobs:
        if j["link"] not in seen:
            seen.add(j["link"])
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

def build_email(jobs):
    if not jobs:
        return "No Dayforce hiring activity found."

    lines = ["US Dayforce Hiring Activity:\n"]

    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. {j['title']}")
        lines.append(f"   {j['link']}")
        lines.append("")

    return "\n".join(lines)

def main():
    print("Fetching jobs...")
    jobs = fetch_jobs()
    print("Raw:", len(jobs))

    jobs = dedupe(jobs)

    seen = load_seen()
    new = []

    for j in jobs:
        if j["link"] not in seen:
            new.append(j)
            seen.add(j["link"])

    save_seen(seen)

    print("New:", len(new))

    body = build_email(new[:25])
    subject = f"Dayforce Hiring Leads: {len(new)}"

    send_email(subject, body)

if __name__ == "__main__":
    main()
