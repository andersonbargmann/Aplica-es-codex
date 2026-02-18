import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def send_email(to_email, subject, body):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not smtp_host or not to_email:
        print("[EMAIL] SMTP_HOST ou destinatário não configurado. E-mail não enviado.")
        return

    sender = smtp_user or "no-reply@helpdesk.local"
    recipients = [to_email] if isinstance(to_email, str) else list(to_email)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.sendmail(sender, recipients, msg.as_string())
    except Exception as exc:
        print(f"[EMAIL] Falha ao enviar e-mail: {exc}")
