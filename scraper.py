import os
import smtplib
from email.mime.text import MIMEText

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

# ❌ EXCLUDE PARTNERS / STAFFING FIRMS
exclude_terms = "-Ascend -Mosaic -Deloitte -EY -KPMG -PwC -RSM -Alight -Accenture -Capgemini -Infosys -TCS -Wipro -Cognizant -Hexaware -TekSystems -InsightGlobal -Kforce -Randstad -RobertHalf -ApexSystems -Collabera"

# 🎯 JOB SEARCHES (END CLIENT BIAS)
job_links = [
    ("LinkedIn - UKG Implementation (End Clients)", f"https://www.linkedin.com/jobs/search/?keywords=UKG%20implementation%20{exclude_terms}"),
    ("LinkedIn - UKG Migration", f"https://www.linkedin.com/jobs/search/?keywords=UKG%20migration%20{exclude_terms}"),
    ("LinkedIn - UKG WFM Transformation", f"https://www.linkedin.com/jobs/search/?keywords=UKG%20WFM%20transformation%20{exclude_terms}"),
    ("LinkedIn - Kronos to UKG Upgrade", f"https://www.linkedin.com/jobs/search/?keywords=Kronos%20upgrade%20UKG%20{exclude_terms}"),
    ("Indeed - UKG Implementation", f"https://www.indeed.com/jobs?q=UKG+implementation+{exclude_terms}"),
]

# 📢 LINKEDIN POSTS (REAL IMPLEMENTATION SIGNALS)
post_links = [
    ("UKG Implementation Announcement", "https://www.google.com/search?q=site:linkedin.com/posts+\"UKG+implementation\""),
    ("UKG Migration / Rollout", "https://www.google.com/search?q=site:linkedin.com/posts+\"UKG+migration\"+OR+\"UKG+rollout\""),
    ("UKG Go Live", "https://www.google.com/search?q=site:linkedin.com/posts+\"UKG+go+live\""),
    ("Kronos to UKG Upgrade", "https://www.google.com/search?q=site:linkedin.com/posts+\"Kronos+to+UKG\""),
    ("Workforce Management Transformation", "https://www.google.com/search?q=site:linkedin.com/posts+\"workforce+management+transformation\""),
]

# 🧠 HIGH-INTENT BUYER SIGNALS (THIS IS THE MONEY SECTION)
buyer_signal_links = [
    ("New HRIS / WFM Selection", "https://www.google.com/search?q=site:linkedin.com/posts+\"selecting+UKG\"+OR+\"evaluating+UKG\""),
    ("Replacing Kronos / Legacy WFM", "https://www.google.com/search?q=site:linkedin.com/posts+\"replacing+Kronos\""),
    ("UKG Dimensions Project", "https://www.google.com/search?q=site:linkedin.com/posts+\"UKG+Dimensions+project\""),
    ("UKG Ready Implementation", "https://www.google.com/search?q=site:linkedin.com/posts+\"UKG+Ready+implementation\""),
]

body = "🔥 UKG END-CLIENT IMPLEMENTATION LEADS\n\n"

body += "🏢 JOB POSTINGS (END CLIENT FOCUSED)\n\n"
for title, url in job_links:
    body += f"{title}\n{url}\n\n"

body += "📢 IMPLEMENTATION SIGNALS (LINKEDIN POSTS)\n\n"
for title, url in post_links:
    body += f"{title}\n{url}\n\n"

body += "💰 HIGH-INTENT BUYER SIGNALS (BEST LEADS)\n\n"
for title, url in buyer_signal_links:
    body += f"{title}\n{url}\n\n"

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG END CLIENT LEADS (IMPLEMENTATIONS & MIGRATIONS)"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
