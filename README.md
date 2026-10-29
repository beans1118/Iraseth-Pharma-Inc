# Iraseth Pharma — Storefront (React) + Admin Console + API

```
storefront/   React source (Vite + React Router) — the customer-facing site
site/         Ready-to-serve build: React storefront + admin console, linked together
admin.html    Admin console (plain HTML/JS) — Superadmin / Admin / Sub-admin
css/ js/ assets/   Admin console files
backend/      Flask + MongoDB API (unchanged architecture; list endpoints now paginated)
legacy-storefront/  Archived old HTML storefront (safe to delete)
```

## Just view it
Serve the **`site/`** folder with any static server (VS Code Live Server works: right-click `site/index.html` → Open with Live Server).
Opening files by double-click will not work for the React build (browsers block module scripts on `file://`).

- Storefront pages: `index.html#/` , `#/catalog`, `#/about`, `#/mission`, `#/leadership`, `#/locations`, `#/contact`
  (hash routing, so it works on any static host with zero server config)
- Admin console: `admin.html` (also reachable via the person icon in the storefront header)
- With no backend running, both apps fall back to the built-in Demo Mode (browser localStorage).

## Develop the React storefront
```bash
cd storefront
npm install
npm run dev      # hot-reload dev server
npm run build    # rebuilds ../site (and copies the admin console into it)
```

## Pagination
All list endpoints accept optional `?page=&limit=` (limit max 200) and return the same shape:
plain JSON array body + `X-Total-Count`, `X-Page`, `X-Page-Size` headers. Omit both params and you get the full array exactly as before.
Covered: products, orders, inventory (stock), session logs, inventory logs, users, backups.

- Storefront catalog: 9 per page, resets to page 1 on search/category change.
- Admin: logs, users and backups page server-side; inventory and orders page client-side (their KPI cards need the whole list).

## Backend
See `backend/README.md` and `DEVELOPMENT-PHASE1-3-README.md`.
