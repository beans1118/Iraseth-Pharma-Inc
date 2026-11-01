# Iraseth Pharma — Inventory Management System

Iraseth Pharma includes a Flask/MongoDB backend, a React/TypeScript employee dashboard, and a separate React customer storefront.

## Project structure

- `backend/` — Flask APIs, authentication, batch inventory, orders, invoices, support, alerts, analytics, and tests
- `frontend/` — employee dashboard (React, TypeScript, Vite)
- `storefront/` — customer-facing React application
- `legacy-storefront/`, `site/`, and root `admin.html` — historical or deployment artifacts; **do not delete or deploy without verifying their use**

## Local development

Requirements: Python 3.12, Node.js/npm, and MongoDB with a working replica set `rs0`. Configure local environment variables without committing secrets.

From `backend/` (in the activated virtual environment):

```powershell
python app.py
python -m pytest tests/ -v
python -m flask --app app routes
```

From `frontend/`:

```powershell
npm install
npm run dev
npm run build
```

From `storefront/`:

```powershell
npm install
npm run dev
npm run build
```

**Caution:** Before running the storefront build, review `storefront/vite.config.js` and output destinations; earlier configurations generated files in `site/`. This repository has legacy UI artifacts that may still be part of deployment.

## Current access policy

- Superadmin: broad administrative access subject to stock safety and audit rules.
- Admin (Board of Directors): read-only.
- Sub-Admin: may create/edit products, receive/release stock through controlled batch operations, and handle order fulfillment; cannot permanently delete products or manage employee accounts.
- Invoice and customer-message staff permissions still require final stakeholder approval.

## Inventory safety

Catalog creation does not add physical stock. Receiving uses batch/lot records. Inventory allocation is expiry-aware; reservations, movement logs, and transaction integrity must not be bypassed. Use `iraseth_test` for automated tests; do not run destructive seeding or migrations against live data.

## Release status

This is an actively developed project, not a certified production deployment. Backend automated tests were reported passing by the project owner after Phase 7; a full role-by-role user acceptance test and deployment/security review are pending.

See `docs/GITHUB-REVIEW-CHECKLIST.md` for the staged-file review and human testing handoff.
