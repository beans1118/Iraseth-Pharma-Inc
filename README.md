# Iraseth Pharma — Ordering site + Inventory backend

## Fastest way to see it working (no install required)

Just open `index.html` or `admin.html` in a browser — double-click the
file, or serve the folder with any static server. **No Python, no
MongoDB, nothing to install.**

If it can't reach a real backend at `http://localhost:5000`, the site
automatically switches to **Demo Mode**: a small sample catalog (30
products with realistic stock levels) and all three role accounts are
created for you, stored only in your browser's local storage. A red
banner at the top says "Demo Mode" whenever this is active, so it's never
confused with real data.

**Demo Mode logins** (shown on the admin login screen too):

| Role | Email | Password |
|---|---|---|
| Superadmin | `superadmin@irasethpharma.com` | `demo-superadmin` |
| Admin | `admin@irasethpharma.com` | `demo-admin` |
| Sub-admin | `subadmin@irasethpharma.com` | `demo-subadmin` |

Everything works in Demo Mode: browsing the catalog, checkout, the
Inventory release/supply buttons, order fulfillment, activity logs, user
management, and backups (backup even downloads a real JSON file to your
computer). The only thing Demo Mode can't do is share data between two
different browsers/devices, or persist across "clear browsing data" —
that's what the real backend is for.

## Running the real backend (Flask + MongoDB)

For production use — real persistence, real multi-user access, real-time
Socket.IO updates pushed across devices — set up the backend in
`backend/README.md`. Once `python app.py` is running at
`http://localhost:5000`, both `index.html` and `admin.html` detect it
automatically and switch off Demo Mode with no configuration needed —
same UI, same features, now backed by a real database.

## Project layout

```
index.html, admin.html   — the two pages (open these directly)
css/styles.css           — all styling
js/                      — frontend logic (config, mock-backend, api, data, main/admin)
assets/                  — logo & images
backend/                 — Flask + MongoDB API (see backend/README.md)
```
