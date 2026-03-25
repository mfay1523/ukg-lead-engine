import os
import smtplib
from email.mime.text import MIMEText

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

job_links = [
    ("LinkedIn - UKG Implementation", "https://www.linkedin.com/jobs/search/?keywords=UKG%20implementation"),
    ("LinkedIn - Kronos Implementation", "https://www.linkedin.com/jobs/search/?keywords=Kronos%20implementation"),
    ("LinkedIn - UKG WFM Implementation", "https://www.linkedin.com/jobs/search/?keywords=UKG%20WFM%20implementation"),
    ("LinkedIn - UKG Dimensions Implementation", "https://www.linkedin.com/jobs/search/?keywords=UKG%20Dimensions%20implementation"),
    ("Indeed - UKG Implementation", "https://www.indeed.com/jobs?q=UKG+implementation"),
    ("Indeed - Kronos Implementation", "https://www.indeed.com/jobs?q=Kronos+implementation"),
    ("Indeed - UKG WFM Implementation", "https://www.indeed.com/jobs?q=UKG+WFM+implementation"),
    ("Google - UKG Implementation Jobs", "https://www.google.com/search?q=UKG+implementation+jobs"),
]

post_links = [
    ("LinkedIn Posts - UKG Implementation", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+implementation"),
    ("LinkedIn Posts - Kronos Implementation", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+Kronos+implementation"),
    ("LinkedIn Posts - UKG Rollout", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+rollout"),
    ("LinkedIn Posts - UKG Migration", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+migration"),
    ("LinkedIn Posts - UKG Go Live", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+go+live"),
    ("LinkedIn Posts - Workforce Management Implementation", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+workforce+management+implementation"),
]

body = "🔥 UKG IMPLEMENTATION LEADS\n\n"

body += "🚀 JOB POSTINGS (IMPLEMENTATION)\n\n"
for title, url in job_links:
    body += f"{title}\n{url}\n\n"

body += "📢 LINKEDIN POSTS (IMPLEMENTATION SIGNALS)\n\n"
for title, url in post_links:
    body += f"{title}\n{url}\n\n"

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Implementation Leads"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
