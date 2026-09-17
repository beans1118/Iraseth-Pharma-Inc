"""
Best-effort outbound email.

Phase 3 keeps SMTP outside the critical API response path by default. Order
requests can return immediately while a small background worker pool sends
email. Set EMAIL_ASYNC=false to restore synchronous behavior.
"""
import atexit
import logging
import smtplib
import ssl
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage

from config import Config

logger = logging.getLogger("iraseth.email")
_executor = ThreadPoolExecutor(
    max_workers=Config.EMAIL_WORKERS,
    thread_name_prefix="iraseth-email",
)
atexit.register(lambda: _executor.shutdown(wait=False, cancel_futures=False))


def send_email(to: str, subject: str, body: str) -> bool:
    if not Config.SMTP_HOST:
        logger.info(
            "[email skipped - SMTP not configured] to=%s subject=%r",
            to,
            subject,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["To"] = to
    msg.set_content(body)

    try:
        if Config.SMTP_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(
                Config.SMTP_HOST,
                Config.SMTP_PORT,
                timeout=Config.SMTP_TIMEOUT_SECONDS,
            ) as server:
                server.starttls(context=context)
                if Config.SMTP_USER:
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(
                Config.SMTP_HOST,
                Config.SMTP_PORT,
                timeout=Config.SMTP_TIMEOUT_SECONDS,
            ) as server:
                if Config.SMTP_USER:
                    server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
                server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def _dispatch_email(to: str, subject: str, body: str) -> None:
    if Config.EMAIL_ASYNC:
        _executor.submit(send_email, to, subject, body)
    else:
        send_email(to, subject, body)


def order_confirmation_email(order: dict) -> None:
    lines_text = "\n".join(
        f"  - {line['qty']} x {line['name']} ({line['unit']})"
        for line in order["lines"]
    )
    body = (
        f"Hi {order['client']},\n\n"
        f"We received your requisition {order['id']} for {order['facility']}.\n\n"
        f"Items:\n{lines_text}\n\n"
        f"Total: PHP {order['total']:,.2f}\n"
        f"Status: {order['status']}\n\n"
        f"Our team will verify stock and pricing and follow up shortly.\n\n"
        f"- Iraseth Pharma Incorporated"
    )
    _dispatch_email(order["email"], f"Order received - {order['id']}", body)


def order_status_email(order: dict, note: str = "") -> None:
    body = (
        f"Hi {order['client']},\n\n"
        f"Your order {order['id']} status has been updated to: {order['status']}.\n"
        + (f"\nNote from our team: {note}\n" if note else "")
        + f"\nTotal: PHP {order['total']:,.2f}\n\n"
        f"- Iraseth Pharma Incorporated"
    )
    _dispatch_email(
        order["email"],
        f"Order {order['id']} - status update: {order['status']}",
        body,
    )
