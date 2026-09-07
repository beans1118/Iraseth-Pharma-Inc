# Iraseth Pharma — Backend (Flask + MongoDB)

A small REST API that replaces the storefront's localStorage-only data with
real persistence: products, orders, and an admin account with login.

## What it does

- **Products** — public catalog reads; create/update/delete require admin login.
- **Orders** — anyone can submit an order (no account needed, same as the
  original storefront). Prices are recalculated server-side from the product
  catalog, never trusted from the browser. Viewing/managing orders requires
  admin login.
- **Auth** — one admin account, email + password, hashed with bcrypt. Login
  returns a JWT that the admin dashboard sends back on every request.
- **Order status + notes** — when an admin changes an order's status or adds
  a note, it's saved to the order and (if SMTP is configured) an email goes
  out to the customer. If SMTP isn't configured, the email is just logged —
  the rest of the app keeps working.

## 1. Prerequisites

- Python 3.10+
- A MongoDB database. Either:
  - **Local**: install MongoDB Community Server and run `mongod`, or
  - **Free hosted option**: create a free cluster at
    [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) and copy
    its connection string.

## 2. Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# now edit .env:
#   - set MONGO_URI to your local or Atlas connection string
#   - set JWT_SECRET to a long random string
#     (generate one with: python -c "import secrets; print(secrets.token_hex(32))")
#   - set SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD to whatever you want your
#     real admin login to be
#   - CORS_ORIGINS: the address your frontend is served from, e.g.
#     http://127.0.0.1:5500 if you're using VS Code's Live Server
```

## 3. Load starting data

This inserts the existing 41-product catalog and creates the admin account:

```bash
python seed.py
```

Re-running it refreshes the product catalog but never touches existing
orders.

## 4. Run it

```bash
python app.py
```

The API is now at `http://localhost:5000/api`. Check it's alive:

```bash
curl http://localhost:5000/api/health
```

## 5. Point the frontend at it

In `js/config.js` (in the site root, one level up from `backend/`), set:

```js
const API_BASE = "http://localhost:5000/api";
```

Then open `index.html` (via a local server, not `file://`) and `admin.html`
as usual. If the API is unreachable, the storefront automatically falls back
to its original offline demo data, so it still works standalone.

## API reference

| Method | Route                          | Auth  | Purpose |
|--------|---------------------------------|-------|---------|
| GET    | `/api/health`                   | none  | Liveness check |
| POST   | `/api/auth/login`                | none  | `{email, password}` → `{token, admin}` |
| GET    | `/api/auth/me`                   | admin | Current admin profile |
| GET    | `/api/products?cat=&q=`          | none  | List/search/filter products |
| GET    | `/api/products/<id>`             | none  | One product |
| POST   | `/api/products`                  | admin | Create product |
| PUT    | `/api/products/<id>`             | admin | Update product |
| DELETE | `/api/products/<id>`             | admin | Delete product |
| POST   | `/api/orders`                    | none  | Submit an order (checkout) |
| GET    | `/api/orders?status=&q=`         | admin | List/search/filter orders |
| GET    | `/api/orders/clients-summary`    | admin | Purchase totals grouped by facility |
| GET    | `/api/orders/<id>`                | admin | One order |
| PATCH  | `/api/orders/<id>`                 | admin | `{status?, note?}` — updates status and/or appends a note; emails the customer on status change |

Admin routes expect `Authorization: Bearer <token>` from `/api/auth/login`.

## Notes on email

`utils/email.py` uses plain `smtplib`. It works with Gmail (with an
[app password](https://support.google.com/accounts/answer/185833)), any
transactional email provider's SMTP credentials (SendGrid, Mailgun, etc.),
or your institution's SMTP server. Leave `SMTP_HOST` blank in `.env` to skip
sending email entirely during development — order creation and status
updates still work, they just log instead of sending.

## Deploying

This is a plain Flask app (`app.py` exposes `app`), so it runs behind any
WSGI server (gunicorn, uWSGI) the same way any Flask app does. Set real
environment variables (not `.env`) in production, and restrict
`CORS_ORIGINS` to your real frontend domain.
