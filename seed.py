"""
Run this once (and again any time you want to reset demo data):

    python seed.py

It will:
  1. Load the product catalog from products_seed.json into MongoDB
     (replacing whatever is currently in the `products` collection).
  2. Create the admin account from SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD
     in .env, if one with that email doesn't already exist.

It does NOT touch the `orders` collection, so real orders are never wiped
by re-running this.
"""
import json
from pathlib import Path

from config import Config
from extensions import db, ensure_indexes
from utils.security import hash_password


def seed_products():
    path = Path(__file__).parent / "products_seed.json"
    products = json.loads(path.read_text())

    db.products.delete_many({})
    db.products.insert_many(products)
    print(f"Seeded {len(products)} products.")


def seed_admin():
    existing = db.admins.find_one({"email": Config.SEED_ADMIN_EMAIL})
    if existing:
        print(f"Admin already exists: {Config.SEED_ADMIN_EMAIL} (skipped).")
        return

    db.admins.insert_one({
        "email": Config.SEED_ADMIN_EMAIL,
        "password_hash": hash_password(Config.SEED_ADMIN_PASSWORD),
        "name": Config.SEED_ADMIN_NAME,
    })
    print(f"Created admin: {Config.SEED_ADMIN_EMAIL}")


if __name__ == "__main__":
    ensure_indexes()
    seed_products()
    seed_admin()
    print("Done.")
