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
from datetime import datetime, timezone

from config import Config
from extensions import db, ensure_indexes
from utils.security import hash_password


def seed_products():
    path = Path(__file__).parent / "products_seed.json"
    products = json.loads(path.read_text())

    db.products.delete_many({})
    db.products.insert_many(products)

    # Log an opening-stock entry for anything seeded with a starting
    # quantity, so its quantity history has a real beginning to measure
    # future releases/supplies against.
    opening_logs = []
    now = datetime.now(timezone.utc).isoformat()
    for p in products:
        if p.get("quantity", 0) > 0 and not db.inventory_logs.find_one({"product_id": p["id"], "action": "opening"}):
            opening_logs.append({
                "product_id": p["id"],
                "product_name": p.get("name", ""),
                "action": "opening",
                "qty": p["quantity"],
                "before": 0,
                "after": p["quantity"],
                "note": "Opening stock (seed)",
                "actor_email": "system@irasethpharma.com",
                "actor_name": "System (seed)",
                "role": "superadmin",
                "at": now,
            })
    if opening_logs:
        db.inventory_logs.insert_many(opening_logs)

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
