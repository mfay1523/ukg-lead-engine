import os
import smtplib
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

search_url = "https://www.google.com/search?q=UKG+WFM+jobs"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(search_url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

leads = []

for g in soup.find_all("div"):
    text = g.get_text(" ", strip=True)

    if "UKG" in text or "Kronos" in text:
        if len(text) < 120:  # keeps it readable
            leads.append(text)

# remove duplicates
leads = list(set(leads))

if leads:
    body = "🔥 UKG Job Summaries Today\n\n" + "\n\n".join(leads[:10])
else:
    body = "No leads found today."

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Job Summaries"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
