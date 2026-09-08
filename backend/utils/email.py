"""
Minimal, best-effort email sending for order confirmations and status updates.

If SMTP_HOST isn't configured (the default for local dev), send_email() just
logs what it would have sent and returns False, instead of the app crashing —
the ordering/admin flow keeps working with no email server hooked up.
"""
import smtplib
import ssl
import logging
from email.message import EmailMessage

from config import Config

logger = logging.getLogger("iraseth.email")


def send_email(to: str, subject: str, body: str) -> bool:
    if not Config.SMTP_HOST:
        logger.info("[email skipped — SMTP not configured] to=%s subject=%r", to, subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["To"] = to
    msg.set_content(body)

    try:
        if Config.SMTP_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.starttls(context=context)
                if Config.SMTP_USER:
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                if Config.SMTP_USER:
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def order_confirmation_email(order: dict) -> None:
    lines_text = "\n".join(
        f"  - {l['qty']} x {l['name']} ({l['unit']})" for l in order["lines"]
    )
    body = (
        f"Hi {order['client']},\n\n"
        f"We received your requisition {order['id']} for {order['facility']}.\n\n"
        f"Items:\n{lines_text}\n\n"
        f"Total: PHP {order['total']:,.2f}\n"
        f"Status: {order['status']}\n\n"
        f"Our team will verify stock and pricing and follow up shortly.\n\n"
        f"— Iraseth Pharma Incorporated"
    )
    send_email(order["email"], f"Order received — {order['id']}", body)


def order_status_email(order: dict, note: str = "") -> None:
    body = (
        f"Hi {order['client']},\n\n"
        f"Your order {order['id']} status has been updated to: {order['status']}.\n"
        + (f"\nNote from our team: {note}\n" if note else "")
        + f"\nTotal: PHP {order['total']:,.2f}\n\n"
        f"— Iraseth Pharma Incorporated"
    )
    send_email(order["email"], f"Order {order['id']} — status update: {order['status']}", body)
