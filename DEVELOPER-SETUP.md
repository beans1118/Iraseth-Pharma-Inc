# Iraseth Pharma developer setup

This is the Windows handover procedure for the Flask/MongoDB backend, React/Vite employee dashboard and Next.js public storefront. The default local database is **`iraseth`**. Git distributes source code, reviewed brochure manifests and approved images; it does not distribute database records, private environment files or accounts.

A fresh setup reconstructs **124 approved brochure products**, including **11 verified galleries / 12 images**. The other 113 products retain neutral placeholders. Complete source records for the three original products (`MED-001`, `MED-002`, `SMP-001`) are unavailable in Git, so they are not fabricated. Where these or other products already exist, setup preserves them and their stock, orders and audit history.

## Prerequisites

Install once: Git, **Python 3.12** with the Windows `py` launcher, **Node.js 24** with npm, MongoDB Community Server, and MongoDB Shell (`mongosh`). Dependency installation needs internet access. Use a normal PowerShell terminal; project setup needs no administrator rights. Installing system software may require administrator rights once.

MongoDB must expose a writable, loopback-only replica set named **rs0**. If one already runs on port 27017, reuse it without reconfiguration. Do not stop or reconfigure an existing database service to follow these instructions. If port 27017 is occupied by a standalone server, arrange replica-set configuration separately or use an unused local port consistently.

For a new, user-owned instance, run in a dedicated terminal:

```powershell
$mongoData = Join-Path $env:LOCALAPPDATA 'IrasethPharma\mongo-rs0'
New-Item -ItemType Directory -Force -Path $mongoData | Out-Null
$mongodExe = (Get-ChildItem 'C:\Program Files\MongoDB\Server\*\bin\mongod.exe' | Sort-Object FullName -Descending | Select-Object -First 1).FullName
& $mongodExe --dbpath $mongoData --replSet rs0 --bind_ip 127.0.0.1 --port 27017
```

Leave it running. In another terminal, run `mongosh --host 127.0.0.1 --port 27017`, then enter this **inside mongosh**, once on the new instance:

```javascript
rs.initiate({_id: "rs0", members: [{_id: 0, host: "127.0.0.1:27017"}]})
// Wait briefly, then confirm true:
db.hello().isWritablePrimary
exit
```

## First-time installation

Clone the company's authorized repository using its GitHub URL, or pull your existing checkout. From the repository root, after saving any local work:

```powershell
git switch main
git pull origin main
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
```

The command creates `backend/.venv` if missing, installs the Python requirements and both npm lockfiles, creates missing private environment files, checks MongoDB/transaction readiness, and prints a **database dry run**. It writes no database records or indexes. Review `database: iraseth`, `source_products: 124`, `image_products: 11` and `status: dry-run`, then apply:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1 -SkipDependencies -Apply
```

Expected result: `created: 124`. Repeating apply creates **zero duplicates**. `-ExecutionPolicy Bypass` applies only to this PowerShell process; it does not change machine policy.

Existing `.env` files are preserved, including the JWT secret, and existing client dotenv files are not shadowed by new files. A conflicting backend file or shell target stops setup. For a clone intentionally configured for the official new database, open `notepad .\backend\.env` and review these values yourself:

```dotenv
APP_ENV=development
DEPLOYMENT_ENVIRONMENT=
MONGO_URI=mongodb://127.0.0.1:27017/?replicaSet=rs0
MONGO_DB_NAME=iraseth
BATCH_MODE=true
FLASK_PORT=5000
```

Preserve your strong private `JWT_SECRET`. Alternatively, keep a separate checkout for another working environment. Never commit actual `.env` files or credentials; only sanitized examples belong in Git.

Any existing document in any collection causes an import skip: setup does not merge into, reset, backfill or repair an occupied database. A previously initialized catalog reports `already-initialized`; another occupied target reports `existing-data-skipped`. Both preserve all products, galleries, staff edits, users, stock, orders, audits and indexes. For an explicitly separate sandbox, supply `-Database iraseth_local_sandbox` consistently. A nondefault MongoDB port similarly requires `-MongoUri 'mongodb://127.0.0.1:27028/?replicaSet=rs0'` consistently. Remote/credentialed URIs, URI database paths and production/staging/test targets are refused by the catalog initializer.

**Existing `iraseth_dev` compatibility:** its runtime settings and data remain valid and are not renamed or migrated. In an already configured checkout, `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1 -Database iraseth_dev -Status` reports that database without changing it. Even an explicit apply reports `legacy-read-only`; the initializer never writes products, indexes, readiness markers or audit entries to `iraseth_dev`, even if empty. Keep using its existing environment to run it, or use a separate checkout for the official `iraseth` setup.

## Local accounts and product restrictions

After catalog setup, create your local login with the existing interactive account bootstrap:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe tools\create_local_test_accounts.py
Pop-Location
```

Enter three distinct local staff identities and unique passwords (12-72 UTF-8 bytes); input is hidden. Confirm the displayed account list with `CREATE THREE TEST USERS`. No accounts are copied or shared, and existing users are never replaced. Later account administration uses Superadmin > Team & Access. Do not run `backend/seed.py`: that historical script deletes/replaces products with blank placeholders.

Brochure products retain provisional identities, empty genuine SKUs, pending selling units, zero quantity/baseline and null internal/public prices. The ordinary public catalog shows Out of Stock / Price Upon Request, with ordering disabled. Receiving, release/reservation, order and invoice identity restrictions remain active. Setup creates batch readiness only after an atomic, zero-stock reconstruction in a fresh eligible database. Genuine supplier SKU/unit confirmation and real stock receiving remain separate staff workflows.

## Start all applications

Start MongoDB first. Use three terminals, each starting at the repository root.

**Flask - port 5000:**

```powershell
cd backend
.\.venv\Scripts\python.exe app.py
```

**Employee dashboard - port 5173:**

```powershell
cd frontend
npm.cmd run dev -- --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`, sign in, and select **All Products**.

**Public storefront - port 3000:**

```powershell
cd storefront-next
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000/products`. Both clients use the same Flask backend and MongoDB `products` collection. Public API pagination is **100 + 24** on a fresh setup; the storefront displays **24/24/24/24/24/4** cards. Existing galleries are stored as validated MongoDB data URLs returned by Flask; no separate image server or hardcoded Next.js catalog is needed.

| Component | Local configuration |
| --- | --- |
| Flask `backend/.env` | `MONGO_DB_NAME=iraseth`, the intended local `MONGO_URI`, `FLASK_PORT=5000` |
| Vite `frontend/.env` | `VITE_DEV_API_TARGET=http://127.0.0.1:5000`, `VITE_API_BASE_URL=` (empty uses its `/api` proxy) |
| Next.js `storefront-next/.env.local` | `CATALOG_API_BASE_URL=http://127.0.0.1:5000`, `NEXT_PUBLIC_STAFF_LOGIN_URL=http://localhost:5173` |
| Flask CORS | Include localhost and 127.0.0.1 origins on ports 5173 and 3000. Setup supplies these for new files. |

API origin values contain **no `/api` suffix**. Next also supports legacy `NEXT_PUBLIC_CATALOG_API_BASE` if its server-only setting is absent. Existing dotenv/shell overrides are preserved; verify the effective values if reusing a checkout. If changing Flask's port, update both client API origins consistently and restart all three apps.

## Subsequent runs and updates

Start the apps with the commands above; no seeding is needed again. Read-only status:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1 -Status
```

After later pulls, refresh dependencies and preview status without overwriting settings/data:

```powershell
git pull origin main
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
```

Press **Ctrl+C** in each app terminal to stop it. Stop a user-owned foreground MongoDB with Ctrl+C after the apps have stopped; keep a shared Windows MongoDB service running. Data is retained. Never delete a database or kill all Node/Python processes as a shutdown method.

## Isolated testing

Use a **separate disposable MongoDB instance on port 27028**. These commands never target the existing development server on 27017. In a dedicated terminal, from the repository root:

```powershell
$testMongoData = Join-Path (Get-Location) ('test-results\mongodb-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $testMongoData | Out-Null
$mongodExe = (Get-ChildItem 'C:\Program Files\MongoDB\Server\*\bin\mongod.exe' | Sort-Object FullName -Descending | Select-Object -First 1).FullName
& $mongodExe --dbpath $testMongoData --replSet rs0 --bind_ip 127.0.0.1 --port 27028
```

Run `mongosh --host 127.0.0.1 --port 27028` in another terminal and initialize that **new disposable** instance inside mongosh:

```javascript
rs.initiate({_id: "rs0", members: [{_id: 0, host: "127.0.0.1:27028"}]})
db.hello().isWritablePrimary
exit
```

From the repository root, use the explicitly guarded test endpoint:

```powershell
$env:IRASETH_TEST_MONGO_PORT = '27028'
$env:IRASETH_LOCAL_VERIFY_URI = 'mongodb://127.0.0.1:27028/?replicaSet=rs0'
Push-Location backend
try {
    .\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Backend regression failed.' }
    .\.venv\Scripts\python.exe -m pytest local_setup_tests -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Setup safety tests failed.' }
} finally {
    Pop-Location
    Remove-Item Env:IRASETH_TEST_MONGO_PORT -ErrorAction SilentlyContinue
    Remove-Item Env:IRASETH_LOCAL_VERIFY_URI -ErrorAction SilentlyContinue
}
```

The disposable regression mode reads the sanitized `.env.test.example`, forces the test database on port 27028 and verifies the actual MongoClient endpoint. It does not read or overwrite real `.env.test`. Without the explicit port flag, historical regression configuration still uses its guarded local test database on 27017; **use the explicit disposable mode for handover verification**. The brochure tool's regression subprocess follows the same test configuration. Stock/invoice examples created by tests are disposable fixtures, not live catalog identity approvals.

Stop the Vite/Next development processes in this checkout before builds, then run:

```powershell
Push-Location frontend
try {
    npm.cmd run test:brochure
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard brochure checks failed.' }
    npm.cmd run test:deployment
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard deployment checks failed.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed.' }
} finally { Pop-Location }
Push-Location storefront-next
try {
    npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw 'Storefront checks failed.' }
    npm.cmd run typecheck
    if ($LASTEXITCODE -ne 0) { throw 'Storefront typecheck failed.' }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Storefront build failed.' }
} finally { Pop-Location }
```

Stop only the disposable MongoDB terminal with Ctrl+C afterward; no database deletion is needed. Test data/logs under `test-results/` are ignored by Git.

## Troubleshooting

Check the API directly:

```powershell
Invoke-RestMethod 'http://127.0.0.1:5000/api/health'
Invoke-RestMethod 'http://127.0.0.1:5000/api/ready'
$catalog = Invoke-RestMethod 'http://127.0.0.1:5000/api/public/products?page=1&limit=100'
$catalog | Select-Object total, page, pageSize, hasMore
($catalog.products | Measure-Object).Count
```

| Symptom | Check / action |
| --- | --- |
| Connection refused or timeout | Start Flask and inspect its terminal. MongoDB/index/replica readiness errors can prevent startup. |
| Health OK, readiness 503 | Flask is running but MongoDB is unavailable. Check its URI and MongoDB process. |
| HTTP 200, `total: 0` | Valid empty public catalog. Check database selection, publication settings and setup status before applying to a fresh target. A misspelled database can read as empty. |
| API has products, storefront unavailable | Verify the effective Next server API origin and restart Next. Its message distinguishes configuration, connection, HTTP and response failures. |
| API has products, dashboard empty/error | Check local login, Vite's effective proxy/direct API settings, its visible error and Flask logs; restart Vite after environment changes. |
| CORS error | Verify backend `CORS_ORIGINS` includes the actual dashboard/storefront browser origins, then restart Flask. |
| Setup reports occupied/legacy database | This is a safe skip. Existing products and original records are preserved. Use a fresh default database or explicit local sandbox; do not erase existing data. |
| Batch readiness error | Use the intended new initialized database or the existing approved legacy configuration. Do not disable batch mode or invent a readiness marker for existing stock. |
| Port already in use | Stop only the app instance you own or choose a free port and update dependent API origins consistently. |
| Build manifest error while Next dev is running | Stop that checkout's Next dev process before building; do not share its generated output directory between dev and build. |

A successful empty response displays **No products published yet**. Filters returning zero from a populated catalog display **No matching products found**. Public counts can legitimately differ from private counts after staff hide records. Genuine supplier SKU/unit evidence, staff passwords, private SMTP credentials and unavailable product-specific images cannot be supplied through Git.

Files changed and verification results: [LOCAL-SETUP-REPORT.md](docs/LOCAL-SETUP-REPORT.md).
