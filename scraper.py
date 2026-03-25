import os
import smtplib
from email.mime.text import MIMEText

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

job_links = [
    ("LinkedIn Jobs - UKG WFM", "https://www.linkedin.com/jobs/search/?keywords=UKG%20WFM"),
    ("LinkedIn Jobs - UKG Ready", "https://www.linkedin.com/jobs/search/?keywords=UKG%20Ready"),
    ("LinkedIn Jobs - Kronos Consultant", "https://www.linkedin.com/jobs/search/?keywords=Kronos%20consultant"),
    ("LinkedIn Jobs - UKG Dimensions", "https://www.linkedin.com/jobs/search/?keywords=UKG%20Dimensions"),
    ("Indeed Jobs - UKG WFM", "https://www.indeed.com/jobs?q=UKG+WFM"),
    ("Indeed Jobs - UKG Ready", "https://www.indeed.com/jobs?q=UKG+Ready"),
    ("Indeed Jobs - Kronos", "https://www.indeed.com/jobs?q=Kronos"),
    ("Indeed Jobs - UKG Payroll", "https://www.indeed.com/jobs?q=UKG+Payroll"),
    ("Google Jobs - UKG Advanced Scheduling", "https://www.google.com/search?q=UKG+Advanced+Scheduling+jobs"),
    ("Google Jobs - UKG Test Assure", "https://www.google.com/search?q=UKG+Test+Assure+jobs"),
]

post_links = [
    ("LinkedIn Posts - UKG WFM", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+WFM"),
    ("LinkedIn Posts - UKG Ready", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+Ready"),
    ("LinkedIn Posts - Kronos", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+Kronos"),
    ("LinkedIn Posts - UKG Healthcare", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+healthcare"),
    ("LinkedIn Posts - UKG Payroll", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+payroll"),
    ("LinkedIn Posts - UKG Dimensions", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+Dimensions"),
    ("LinkedIn Posts - UKG Implementation", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+UKG+implementation"),
    ("LinkedIn Posts - Workforce Management", "https://www.google.com/search?q=site%3Alinkedin.com%2Fposts+workforce+management+UKG"),
]

body = "🔥 UKG Daily Lead Digest\n\n"

body += "JOB POSTING SEARCHES\n\n"
for title, url in job_links:
    body += f"{title}\n{url}\n\n"

body += "LINKEDIN POST SEARCHES\n\n"
for title, url in post_links:
    body += f"{title}\n{url}\n\n"

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Daily Lead Digest"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
