# Iraseth Pharma — Storefront + Admin

## What changed in this pass

**Header/logo fix** — the header is now white instead of navy. Your logo's
navy-blue lettering ("RASETH", "PHARMA", "Incorporated") was nearly the same
color as the old navy header background, so half the logo was effectively
unreadable there; only the red parts stood out. On white, the full logo
reads clearly.

**UI/UX polish** (same layout/sections as before, per your call — nothing
was restructured):
- Fixed a real bug, not just a style nit: on any screen under 980px wide,
  the entire nav — including the "Order slip" button — disappeared with no
  way to bring it back. Added a working hamburger menu.
- Same bug existed in the admin sidebar on mobile; now becomes a horizontal
  bar instead of vanishing.
- More consistent hover states, shadows, and transitions on buttons and
  cards throughout.

**Backend** — a real Python (Flask) + MongoDB API now backs the site:
products, orders, admin login, and order status/notes with email
notifications. See `backend/README.md` for full setup.

## Running it

### Frontend only (no backend)
Just open `index.html` / `admin.html` through any static file server (not
`file://`, since fetch calls need an http origin). It'll automatically fall
back to the built-in offline demo data — same behavior as before this pass.

Quick option:
```bash
python -m http.server 8000
# then visit http://localhost:8000
```

### Frontend + real backend
1. Set up and run the backend — see `backend/README.md` (roughly:
   `pip install -r requirements.txt`, fill in `.env`, `python seed.py`,
   `python app.py`).
2. Confirm `js/config.js` points at it (`http://localhost:5000/api` by
   default — matches the backend's default port).
3. Serve the frontend as above and open it in a browser.

Once both are running: products load from MongoDB, checkout creates a real
order in the database, and the admin dashboard (login with whatever you set
`SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` to) shows real orders, lets you
change status, and add notes — both of which are stored on the order and
trigger a customer email if `SMTP_HOST` is configured.

Admin demo login (used only when the backend isn't reachable):
`admin@irasethpharma.com` / `iraseth2026`

## File map

```
index.html, admin.html       storefront + admin pages
css/styles.css                all styling
js/config.js                  API_BASE — point this at your backend
js/api.js                     fetch wrapper for the backend API
js/data.js                    demo product catalog (offline fallback) + Cart/Orders helpers
js/main.js                    storefront logic (catalog, cart, checkout)
js/admin.js                   admin login + dashboard logic
assets/                       logo, CEO photo, ISO badge
backend/                      Flask + MongoDB API — see backend/README.md
```
