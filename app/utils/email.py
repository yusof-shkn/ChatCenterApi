from smtplib import SMTP

def send_email(to_email, subject, body):
    with SMTP("smtp.example.com") as smtp:
        smtp.sendmail("from_email@example.com", to_email, f"Subject: {subject}\n\n{body}")
