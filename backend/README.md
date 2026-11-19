# Iraseth Pharma API

Flask, MongoDB and Socket.IO backend for the employee dashboard and Next.js storefront. Current startup and deployment instructions are in [the staging plan](../docs/STAGING-DEPLOYMENT-PLAN.md); historical backend design is in [docs/history](../docs/history/DEVELOPMENT-PHASE1-3-README.md).

## Local setup

Use Python 3.12 and a local MongoDB replica set `rs0`. From `backend/`, create/activate a virtual environment and install `requirements.txt`. Create `.env` from the example only if absent, then configure the intended local target and a unique JWT secret. Preserve existing environment files and inventory. `python app.py` starts the local API; `GET /api/health` and `GET /api/ready` check liveness and readiness.

**Do not run `seed.py` on an existing database.** It deletes/replaces products. It is retained as historical tooling, not a staging or test setup command. No startup/build command imports products or copies development data. Do not bootstrap users, migrate inventory or create a readiness marker without separate authorization for the exact database. Use the staging plan's guarded initializer for a separately authorized, empty `iraseth_staging` target.

## Isolated regression tests

From an activated backend virtual environment:

```powershell
python -m pip install -r requirements-dev.txt
# Only when .env.test does not already exist:
if (-not (Test-Path -LiteralPath .env.test)) { Copy-Item -LiteralPath .env.test.example -Destination .env.test }
python -m pytest tests -q -p no:cacheprovider
```

The test configuration locks writes to `mongodb://127.0.0.1:27017/?replicaSet=rs0`, database `iraseth_test`, before importing Flask. It refuses another target and cleans disposable fixtures. The example JWT key is test-only, not a real credential or deployment setting. PDF integration tests simulate identities only inside this isolated database; they do not approve genuine live SKU/unit values. For offline PDF reconstruction, install optional `requirements-brochure.txt` separately. Browser UAT and the current test evidence are linked from [the verification checklist](../docs/GITHUB-REVIEW-CHECKLIST.md).

## Current API and safeguards

- Public `/api/public/products` returns an allowlisted live catalog. Public inquiry submission and reference tracking use their dedicated endpoints; anonymous clients do not use the private product API.
- Authenticated `/api/products` serves the existing product collection and metadata/gallery editor. Image-only updates validate decoded images and append transactional audit events. No gallery filesystem upload directory is required: image data URLs persist in MongoDB.
- Operational inventory uses batch APIs when batch mode is enabled. Receiving, releases, expiry-aware reservations and fulfillment preserve transaction/audit safeguards; legacy quantity routes are blocked in batch mode.
- Public inquiries are reviewed into one Pending official order. Approval/reservation, fulfillment and explicitly priced invoices retain existing permissions and stock rules.
- Provisional PDF identities remain blocked from stock/order/invoice operations until authorized staff confirm genuine SKU and selling unit. Metadata/image edits do not supply stock or public prices.
- Board Admin is read-only. Superadmin and Sub-admin access remains subject to route permissions, identity gates and workflow validation. Users, private stock, session records and costs are not exposed by the public catalog.
- Verified customer communication requires real SMTP in staging. Automated UAT uses an in-memory mail double and does not establish external delivery.

## Deployment snapshot

Render builds from the repository root with `pip install -r backend/requirements.txt` and starts `gunicorn --config backend/gunicorn.conf.py app:app`. Keep `docs/brochure/` available to protected review/import tooling. Use Atlas staging-only credentials and `iraseth_staging` only after separately authorized provisioning. Real environments, secrets, dependencies, database exports and generated builds are ignored. Git contains source/media, not any of the 127 local product records or their uploaded galleries.
