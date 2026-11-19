"""Interactive, non-destructive bootstrap for a NEW local Iraseth test database.

Run from backend/: python tools/create_local_test_accounts.py
Requires the existing project's .env and MongoDB single-node replica set rs0.
Supports the default iraseth and explicit local sandbox targets.
Refuses to operate on any database already containing a user; use Team & Access then.
"""
from __future__ import annotations

import getpass
import ipaddress
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ROLES = (("superadmin", "Superadmin"), ("admin", "Board Admin (view only)"), ("subadmin", "Sub-Admin (operations)"))


def ensure_local_target(config):
    if config.APP_ENV != "development":
        raise ValueError("APP_ENV must be development. This tool is only for local testing.")
    if config.MONGO_DB_NAME == 'iraseth' or config.MONGO_DB_NAME.startswith('iraseth_local_'):
        from tools.setup_local_catalog import validate_target
        validate_target(config.MONGO_DB_NAME, config.MONGO_URI)
    elif config.MONGO_DB_NAME not in ("iraseth_dev", "iraseth_uat"):
        raise ValueError("Use the default local iraseth or an explicit approved local sandbox target.")
    uri = config.MONGO_URI
    if not uri.startswith("mongodb://") or "," in uri.split("/", 3)[2]:
        raise ValueError("Only a single local mongodb:// host is permitted.")
    parsed = urlsplit(uri)
    host = parsed.hostname
    if host not in ("localhost", "127.0.0.1", "::1"):
        try:
            if not ipaddress.ip_address(host or "").is_loopback:
                raise ValueError("MongoDB must be local.")
        except ValueError:
            raise ValueError("MongoDB must use localhost or a loopback address.") from None


def collect_accounts(input_fn=input, password_fn=getpass.getpass):
    accounts = []
    emails = set()
    for role, label in ROLES:
        print(f"\n{label}")
        name = input_fn("  Display name: ").strip()
        email = input_fn("  Email address: ").strip().lower()
        if not name or len(name) > 120 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Names and valid email addresses are required.")
        if email in emails:
            raise ValueError("All three accounts need distinct email addresses.")
        password = password_fn("  New password (hidden): ")
        check = password_fn("  Confirm password: ")
        if password != check or len(password) < 12 or len(password.encode("utf-8")) > 72:
            raise ValueError("Password mismatch or password length not between 12 and 72 UTF-8 bytes.")
        if password.lower() in ("change-me-superadmin", "change-me-admin", "change-me-subadmin"):
            raise ValueError("Do not use old placeholder passwords.")
        accounts.append({"name": name, "email": email, "role": role, "password": password})
        emails.add(email)
    return accounts


def main():
    # Configuration and connection are loaded only when invoked, not when imported by tests.
    from config import Config
    from extensions import db
    from utils.security import hash_password

    ensure_local_target(Config)
    db.command("ping")
    if db.users.count_documents({}, limit=1):
        raise ValueError("Users already exist in this database. No changes made. Use Superadmin > Team & Access.")

    print("Local development only. No products, inventory, orders, or existing accounts will be changed.")
    print(f"Target database: {Config.MONGO_DB_NAME} at local MongoDB")
    accounts = collect_accounts()
    print("\nAccounts to create:")
    for item in accounts:
        print(f"  {item['role']:12} {item['email']}")
    if input("Type CREATE THREE TEST USERS to confirm: ").strip() != "CREATE THREE TEST USERS":
        print("Cancelled; database unchanged.")
        return 1
    docs = [{"name": a["name"], "email": a["email"], "role": a["role"],
             "password_hash": hash_password(a["password"]), "is_active": True}
            for a in accounts]
    # Ensure uniqueness before transaction, then repeat emptiness guard inside it.
    db.users.create_index("email", unique=True)
    with db.client.start_session() as session:
        with session.start_transaction():
            if db.users.count_documents({}, limit=1, session=session):
                raise ValueError("Another user was created while setting up. No changes made.")
            db.users.insert_many(docs, ordered=True, session=session)
    print("Created three test users. Passwords were not stored in source or printed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f"Setup stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
