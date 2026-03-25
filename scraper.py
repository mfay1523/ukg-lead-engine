import os
import smtplib
from email.mime.text import MIMEText

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

leads = [
    "Search LinkedIn Jobs: UKG WFM https://www.linkedin.com/jobs/search/?keywords=UKG%20WFM",
    "Search LinkedIn Jobs: Kronos https://www.linkedin.com/jobs/search/?keywords=Kronos",
    "Search Indeed: UKG https://www.indeed.com/jobs?q=UKG",
    "Search Indeed: UKG Ready https://www.indeed.com/jobs?q=UKG+Ready",
    "Search Indeed: Kronos https://www.indeed.com/jobs?q=Kronos",
    "Search Google Jobs: UKG Dimensions https://www.google.com/search?q=UKG+Dimensions+jobs",
]

body = "🔥 UKG Lead Links Today\n\n" + "\n\n".join(leads)

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Lead Links"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
