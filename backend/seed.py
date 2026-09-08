"""
Run this once (and again any time you want to reset demo data):

    python seed.py

It will:
  1. Load the product catalog from products_seed.json into MongoDB
     (replacing whatever is currently in the `products` collection). Every
     product starts with an empty name/description and quantity 0 — fill in
     the real catalog through the Superadmin "Add product" screen (or a
     follow-up seed file) once it's ready.
  2. Create the three seed staff accounts (superadmin / admin / subadmin)
     from Config.SEED_USERS, if accounts with those emails don't already
     exist.

It does NOT touch `orders`, `sessions`, or `inventory_logs`, so real
activity is never wiped by re-running this.
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
    print(f"Seeded {len(products)} products (all empty — fill in real data via the admin UI).")


def seed_users():
    for user in Config.SEED_USERS:
        if db.users.find_one({"email": user["email"]}):
            print(f"User already exists: {user['email']} (skipped).")
            continue
        db.users.insert_one({
            "email": user["email"],
            "password_hash": hash_password(user["password"]),
            "name": user["name"],
            "role": user["role"],
        })
        print(f"Created {user['role']}: {user['email']} — change this password immediately.")


if __name__ == "__main__":
    ensure_indexes()
    seed_products()
    seed_users()
    print("Done.")
