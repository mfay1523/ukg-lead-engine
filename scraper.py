import os
import smtplib
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

search_urls = [
    "https://www.indeed.com/jobs?q=UKG",
    "https://www.indeed.com/jobs?q=Kronos",
    "https://www.indeed.com/jobs?q=UKG+Dimensions",
    "https://www.indeed.com/jobs?q=UKG+Ready"
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

keywords = ["ukg", "kronos", "dimensions", "ukg ready", "workforce management", "wfm"]
seen = set()
leads = []

for url in search_urls:
    try:
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a", href=True):
            title = a.get_text(" ", strip=True)
            href = a["href"]

            if not title:
                continue

            lower_title = title.lower()

            if not any(word in lower_title for word in keywords):
                continue

            if href.startswith("/"):
                full_link = "https://www.indeed.com" + href
            else:
                full_link = href

            key = (title, full_link)
            if key in seen:
                continue

            seen.add(key)
            leads.append(f"{title}\n{full_link}")

    except Exception as e:
        leads.append(f"Search failed for {url}: {e}")

if leads:
    body = "🔥 UKG Leads Today\n\n" + "\n\n".join(leads[:15])
else:
    body = "No leads found today."

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Leads"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
