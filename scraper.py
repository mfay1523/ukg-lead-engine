import os
import smtplib
from email.mime.text import MIMEText

# Test leads
leads = [
    "Healthcare – UKG WFM Implementation (Score: 10)",
    "Retail – UKG Ready Optimization (Score: 9)",
    "Manufacturing – Kronos Upgrade (Score: 8)"
]

body = "🔥 UKG Leads Today\n\n" + "\n".join(leads)

email_address = os.environ["EMAIL_ADDRESS"]
email_password = os.environ["EMAIL_APP_PASSWORD"]

msg = MIMEText(body)
msg["Subject"] = "🔥 UKG Leads"
msg["From"] = email_address
msg["To"] = email_address

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(email_address, email_password)
    server.send_message(msg)
