import os
import smtplib
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

url = "https://www.indeed.com/jobs?q=UKG+Kronos&l="

headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)

soup = BeautifulSoup(response.text, "html.parser")

jobs = soup.find_all("h2")

leads = []

for job in jobs[:10]:
    title = job.text.strip()
    if "UKG" in title or "Kronos" in title:
        leads.append(title)

if leads:
    body = "🔥 UKG Leads Today\n\n" + "\n".join(leads)
else:
    body = "No leads found today."

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Leads"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
