# tools/inbox_reader.py
import os
import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv()

IMAP_HOST     = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT     = int(os.getenv("IMAP_PORT", 993))
IMAP_USER     = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")


def fetch_replies(approved_emails: list[str]) -> list[dict]:
    """
    Connects to Gmail via IMAP.
    Fetches the newest unread email from each approved candidate only.
    Returns list of {from_email, subject, body} dicts.
    """

    if not IMAP_USER or not IMAP_PASSWORD:
        raise Exception("IMAP credentials not set in .env")

    replies = []

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("inbox")

        for candidate_email in {email.lower() for email in approved_emails}:
            status, message_ids = mail.search(None, "UNSEEN", "FROM", candidate_email)
            if status != "OK" or not message_ids[0]:
                continue

            # IMAP sequence numbers grow with arrival order; process only the latest reply.
            latest_message_id = message_ids[0].split()[-1]
            status, data = mail.fetch(latest_message_id, "(RFC822)")
            if status != "OK" or not data or not data[0]:
                continue

            message = email.message_from_bytes(data[0][1])
            from_email = extract_email_address(message.get("From", "")).lower()
            if from_email != candidate_email:
                continue

            replies.append({
                "from_email": from_email,
                "subject": decode_subject(message.get("Subject", "")),
                "body": extract_body(message),
            })
            print(f"  Found latest unread reply from: {from_email}")
    finally:
        mail.logout()
    return replies


def extract_email_address(from_header: str) -> str:
    """
    Extracts clean email from header.
    'John Smith <john@example.com>' → 'john@example.com'
    """
    if "<" in from_header:
        return from_header.split("<")[1].strip(">").strip()
    return from_header.strip()


def decode_subject(subject: str) -> str:
    """Decodes email subject which may be encoded."""
    decoded = decode_header(subject)
    parts   = []
    for part, encoding in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(encoding or "utf-8"))
        else:
            parts.append(str(part))
    return " ".join(parts)


def extract_body(message) -> str:
    """Extracts plain text body from email."""
    body = ""

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8")
                    break
                except Exception:
                    continue
    else:
        try:
            body = message.get_payload(decode=True).decode("utf-8")
        except Exception:
            body = str(message.get_payload())

    return body.strip()
