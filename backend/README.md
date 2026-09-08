# Iraseth Pharma — Backend (Flask + MongoDB + Socket.IO)

A REST + real-time API powering the storefront and the role-based backend
console: live inventory tracking, purchase orders, and a full audit trail
(who logged in/out and every stock change), gated by three roles.

## Roles

| Role | Can do |
|---|---|
| **Superadmin** | Everything: create/edit/delete products, add/deduct stock, manage staff accounts & roles, view every log (sessions + inventory), run backups. |
| **Admin** | View-only: inventory levels, orders, clients, and **all logs** (who logged in/out, when, how long, and every stock add/deduct). Cannot change stock, orders, or accounts. |
| **Sub-admin** | Add/deduct stock (release + supply), update purchase order status, view clients. Cannot see logs, manage products, or manage accounts. |

## What it does

- **Inventory** (`/api/inventory`) — the real-time tracking system itself.
  `GET` lists current stock; `POST /<id>/release` deducts (a product went
  out) and `POST /<id>/supply` adds (restock). Every change is written to
  `inventory_logs` (who, role, product, qty, before→after, note, timestamp)
  and pushed live over Socket.IO to every connected dashboard.
- **Products** (`/api/products`) — the catalog itself (name, description,
  category, unit, reorder level, price). Only Superadmin can create/edit/
  delete a product. Quantity is never edited here — only through
  `/api/inventory`, so every stock change is always logged.
- **Orders** (`/api/orders`) — anyone can submit an order (checkout, no
  login). Prices are recalculated server-side, never trusted from the
  browser. Marking an order **Fulfilled** automatically releases stock for
  every line item and logs it against that order.
- **Auth** (`/api/auth`) — login/logout write to `sessions`: `login_at`,
  `logout_at`, `duration_seconds`, `role`, IP, user agent. This *is* the
  "who logged in/out, when, for how long, as what role" log.
- **Logs** (`/api/logs`) — Superadmin + Admin only. `/sessions` = login
  activity, `/inventory` = every stock add/deduct.
- **Users** (`/api/users`) — Superadmin only. Create staff accounts, change
  roles, remove accounts.
- **Backup** (`/api/backup`) — Superadmin only. `POST /run` snapshots
  products, orders, users (no password hashes), sessions, and inventory
  logs to a timestamped JSON file under `backend/backups/`.

## 1. Prerequisites

- Python 3.10+
- A MongoDB database — local `mongod`, or a free
  [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) cluster.

## 2. Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# now edit .env:
#   - MONGO_URI: your local or Atlas connection string
#   - JWT_SECRET: a long random string
#     (generate one with: python -c "import secrets; print(secrets.token_hex(32))")
#   - SEED_SUPERADMIN_*/SEED_ADMIN_*/SEED_SUBADMIN_*: the three real logins
#     you want to start with — change every password before going live
#   - CORS_ORIGINS: the address your frontend is served from
```

## 3. Load starting data

```bash
python seed.py
```

This inserts 30 empty placeholder products (name/description blank, quantity
0 — fill in the real catalog through the Superadmin console once it's ready)
and creates the three seed accounts if they don't already exist. It never
touches existing orders, sessions, or inventory logs, so it's safe to re-run.

## 4. Run it

```bash
python app.py
```

This starts the API **and** the Socket.IO real-time layer together (via
`socketio.run`, not a plain `app.run`) at `http://localhost:5000/api`.

```bash
curl http://localhost:5000/api/health
```

## 5. Point the frontend at it

In `js/config.js` (site root, one level up from `backend/`):

```js
const API_BASE = "http://localhost:5000/api";
```

`SOCKET_BASE` is derived from this automatically. Then open `index.html`
and `admin.html` through a local server (not `file://`).

## API reference

| Method | Route | Role | Purpose |
|---|---|---|---|
| GET | `/api/health` | none | Liveness check |
| POST | `/api/auth/login` | none | `{email, password}` → `{token, user}` |
| POST | `/api/auth/logout` | any | Closes the session log (logout_at + duration) |
| GET | `/api/auth/me` | any | Current user profile |
| GET | `/api/products?category=&q=` | none | List/search catalog |
| POST / PUT / DELETE | `/api/products[/<id>]` | superadmin | Manage the catalog (not quantity) |
| GET | `/api/inventory` | any | Live stock levels |
| POST | `/api/inventory/<id>/release` | superadmin, subadmin | Deduct stock (logged) |
| POST | `/api/inventory/<id>/supply` | superadmin, subadmin | Add stock (logged) |
| POST | `/api/orders` | none | Submit an order (checkout) |
| GET | `/api/orders?status=&q=` | any | List/search orders |
| GET | `/api/orders/clients-summary` | any | Purchase totals by facility |
| PATCH | `/api/orders/<id>` | superadmin, subadmin | Update status/note (Fulfilled deducts stock) |
| GET | `/api/logs/sessions?role=&user=` | superadmin, admin | Login/logout audit trail |
| GET | `/api/logs/inventory?action=&product=` | superadmin, admin | Stock change audit trail |
| GET / POST / PATCH / DELETE | `/api/users[/<email>]` | superadmin | Manage staff accounts & roles |
| POST | `/api/backup/run` | superadmin | Snapshot everything to JSON |
| GET | `/api/backup` | superadmin | List past backups |
| GET | `/api/backup/<file>/download` | superadmin | Download a backup file |

All protected routes expect `Authorization: Bearer <token>` from
`/api/auth/login`.

## Real-time (Socket.IO)

Connect to `SOCKET_BASE` and `emit("join", {room: "inventory"})` (any role)
and/or `emit("join", {room: "logs"})` (superadmin/admin) to receive:

- `stock:update` — a product's new quantity/status
- `log:inventory` — a new add/release log entry
- `log:session` — a new login/logout log entry

## Notes on email

`utils/email.py` uses plain `smtplib`. Leave `SMTP_HOST` blank in `.env` to
skip sending during development — order creation/status updates still work,
they just log instead of sending.

## Backups

Backups are triggered manually (`POST /api/backup/run`) or on a schedule you
set up yourself (a cron job or scheduled task hitting that endpoint, e.g.
daily at 2am). Files land in `backend/backups/` — back that folder up
off-server too (e.g. sync it to cloud storage) so a server failure can't
take the backups with it.

## Deploying

Plain Flask app (`app.py` exposes `app`) with Socket.IO attached, so it runs
behind gunicorn with the `eventlet` or `gevent` worker class (needed for
WebSockets), e.g.: `gunicorn --worker-class eventlet -w 1 app:app`. Set real
environment variables (not `.env`) in production, and restrict
`CORS_ORIGINS` to your real frontend domain.
