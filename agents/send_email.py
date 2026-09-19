# agents/send_emails.py
import os
import smtplib
import uuid
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from state import ChildState    # ← ChildState

load_dotenv()

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_NAME     = os.getenv("EMAIL_FROM_NAME", "The Hiring Team")


def send_single_email(to: str, subject: str, body: str) -> dict:
    message_id = f"<{uuid.uuid4()}@interview-agent>"

    msg = MIMEMultipart("alternative")
    msg["From"]       = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"]         = to
    msg["Subject"]    = subject
    msg["Message-ID"] = message_id
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to, msg.as_string())

    return {"to": to, "message_id": message_id}


def send_email_node(state: ChildState) -> dict:   # ← ChildState, ONE email
    """
    Sends ONE email to ONE candidate.
    Reads email_draft from state.
    Writes sent_email to state.
    """

    draft = state.get("email_draft", {})

    if not draft:
        return {"error": "send_email: no email draft found in state."}

    try:
        result = send_single_email(
            to      = draft["to"],
            subject = draft["subject"],
            body    = draft["body"],
        )
        print(f"  ✓ Sent to {state['candidate_name']}")
        return {"sent_email": result}

    except Exception as e:
        return {"error": f"send_email failed for {draft.get('to')}: {e}"}
