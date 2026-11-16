# First staging deployment — Iraseth Pharma

Prepared locally on `feature/storefront-modernization`, 16 November 2026. **No services have been created and nothing has been deployed, committed or pushed.** This is the procedure for a later authorized staging deployment. It does not authorize importing inventory, brochure candidates or customer data.

The paragraph above records the original preparation state. See [the later local commit review](LOCAL-COMMIT-REVIEW.md) for the reviewed source snapshot and latest 233-test/17-scenario verification. Local commits do not provision or deploy anything, and historical test counts below remain preparation evidence.

**1. Deployment layout and decisions**

| Component | Host/project | Project root | Runtime/build/start |
| --- | --- | --- | --- |
| Flask API | Render Python web service, staging only | **Repository root; leave Root Directory blank** | `PYTHON_VERSION=3.12.10` matches the tested local Python; build `pip install -r backend/requirements.txt`; start `gunicorn --config backend/gunicorn.conf.py app:app` |
| Public storefront | Separate Vercel project | `storefront-next` | Next.js preset; Node **24.x**; install `npm ci`; build `npm run build`; output default `.next`, **no override and no static export** |
| Employee dashboard | Separate Vercel project | `frontend` | Vite preset; Node **24.x**; install `npm ci`; build `npm run build`; output `dist`; `vercel.json` supplies SPA fallback |
| Database | MongoDB Atlas | New isolated `iraseth_staging` database | Atlas SRV/TLS connection, sessions and multi-document transactions; staging-only credentials |

Choose real staging hostnames before setting environment values. All `REPLACE_*` values in the templates are placeholders, not provisioned services or approved staff identities. Keep this staging environment separate from any future production projects. Do not point a Preview or Production environment at `iraseth_dev`, `iraseth_test` or a production database.

Render's repository root is important: `backend/modules/brochure/service.py` reads `docs/brochure` alongside `backend`. Files outside Render's configured Root Directory are unavailable at build/runtime. Gunicorn changes its process working directory to `backend` after the full repository is available. [Render monorepo rules](https://render.com/docs/monorepo-support)

The startup configuration binds `0.0.0.0:$PORT` (Render supplies `PORT`), uses one `gthread` worker and eight threads, and creates MongoClient after the worker starts. This matches the current `SocketIO(async_mode='threading')`; explicit `simple-websocket` supplies WebSocket support. Do not use an eventlet worker, preload MongoClient, or add workers/instances without designing a shared Socket.IO message queue. The current React dashboard uses HTTP polling. [Flask deployment on Render](https://render.com/docs/deploy-flask), [Flask-SocketIO deployment](https://flask-socketio.readthedocs.io/en/latest/deployment.html)

**2. Prepared files and configuration fixes**

- `backend/gunicorn.conf.py`: production server bind/thread/worker/log settings.
- `backend/requirements.txt`: explicit SRV DNS support, tested Flask-Compress pin and WebSocket dependency.
- `backend/config.py`, `backend/utils/deployment.py`: a staging target must use production safeguards and the Atlas `iraseth_staging` database. Template secrets and unauthenticated production Socket.IO rooms are rejected.
- `backend/tools/initialize_staging.py`: read-only by default; guarded initialization of a completely empty staging database only. Never run the destructive catalog seeder for staging.
- `frontend/src/api-url.ts`, `api.ts`, `SupportChat.tsx`, `BrochureReview.tsx`: all ordinary API calls, support requests and authenticated brochure downloads use the configured Flask origin. Empty local configuration retains the existing Vite proxy.
- `frontend/vite.config.ts`: Vercel requires a valid HTTPS API origin, without `/api`, credentials or query parameters. `frontend/src/vite-env.d.ts` declares Vite's environment types.
- `frontend/vercel.json`: Vite build settings and direct-link fallback, including `/support` reloads. `storefront-next/vercel.json`: Next.js build settings; SSR and route handlers remain enabled.
- `storefront-next/next.config.mjs`: Vercel builds require HTTPS API and employee-app origins. `.env.example` documents the server-only API setting and public employee-app URL.
- Deployment regression checks: `frontend/tests/deployment-config.mjs`, `storefront-next/tests/deployment-config.mjs`, `backend/tests/test_staging_configuration.py`; dashboard package script `test:deployment`.
- The storefront now uses **Next.js 15.5.29 and React/React DOM 19.1.10**. The confirmed nested dependency issues are resolved with **PostCSS 8.5.32** and **Sharp 0.35.5**; npm overrides prevent the vulnerable nested versions from returning. The installed tree and lockfile agree. These changes retain the existing Next.js major version; the native image pipeline and browser workflows passed. [Official Next.js 15.5.29 security release](https://github.com/vercel/next.js/releases/tag/v15.5.29)

**3. Environment settings**

Use these reference templates; **do not copy them over local `.env` or `.env.test` files**:

- [Render backend](staging/backend.env.example)
- [Vercel storefront](staging/storefront.env.example)
- [Vercel dashboard](staging/dashboard.env.example)

Enter real values through each provider's environment/secret settings. Never add credentials to Git, Vercel public variables, query strings or shared screenshots.

| Setting | Where | Required value/meaning |
| --- | --- | --- |
| `APP_ENV` | Render | `production`, even though the deployment is staging, to activate existing production safeguards |
| `DEPLOYMENT_ENVIRONMENT` | Render | `staging`; startup then refuses local/non-Atlas targets and any database name except `iraseth_staging` |
| `MONGO_URI` | Render secret | Atlas driver SRV string; percent-encode credential characters; `retryWrites=true&w=majority`; retain TLS; **do not append local `replicaSet=rs0`** |
| `MONGO_DB_NAME` | Render | `iraseth_staging` |
| `JWT_SECRET` | Render secret | New cryptographically random secret, at least 32 characters, unique to staging; template placeholder is refused |
| `CORS_ORIGINS` | Render | Exact comma-separated dashboard and storefront HTTPS origins, no trailing `/`, paths or `*`; include the actual stable aliases used for UAT |
| `SOCKET_AUTH_REQUIRED` | Render | `true` |
| `TRUST_PROXY_COUNT` | Render | `1` for the planned direct Render edge → Flask topology; verify actual forwarding at deployment; reassess before adding another proxy |
| `BATCH_MODE` | Render | `false` only during initial empty bootstrap; change to `true` after the guarded initialization, before operational UAT |
| `SEED_*` staff settings | Render secrets | Genuine distinct staging staff emails, names and unique 12–72 UTF-8-byte passwords for Superadmin, Board Admin and operator; no default passwords |
| `SMTP_*` | Render secrets/settings | Real provider settings and verified sender; STARTTLS on port `587`; see email requirements below |
| `EMAIL_ASYNC` | Render | `false` for initial staging verification; the existing async executor is best-effort and not a durable mail queue |
| `CATALOG_API_BASE_URL` | Vercel storefront server environment | Backend HTTPS **origin only**, without `/api`; supplies catalog, inquiries and tracking |
| `NEXT_PUBLIC_STAFF_LOGIN_URL` | Vercel storefront | Dashboard HTTPS origin; public/build-time, rebuild after changing |
| `VITE_API_BASE_URL` | Vercel dashboard | Backend HTTPS **origin only**, without `/api`; public/build-time, rebuild after changing |

Set the frontend values for every Vercel environment actually used by this staging project. A dedicated project's Production alias can still represent the staging environment; the word “Production” in Vercel must never imply production database credentials. Bind Preview deployments to staging only when explicitly intended, and list each allowed stable origin explicitly. Avoid allowing arbitrary `*.vercel.app` origins.

`VITE_DEV_API_TARGET` only controls the local Vite proxy; it cannot configure deployed static JavaScript. `NEXT_PUBLIC_CATALOG_API_BASE` remains a legacy fallback in the code, but new Vercel builds require the server-only `CATALOG_API_BASE_URL` setting. Neither frontend needs MongoDB credentials, JWT signing secrets, SMTP credentials or staff passwords.

**4. Atlas preparation — only after authorization to create staging**

1. Create an isolated Atlas staging project/cluster or a clearly isolated supported replica-set cluster/database. Do not restore/copy local or production data. Use `iraseth_staging`, initially empty.
2. Create a database user restricted to the staging cluster and `readWrite` privileges on **iraseth_staging only**, including the application's index creation and collection operations. Avoid project-wide `readWriteAnyDatabase`. Restrict the Atlas network access list to the actual Render service's outbound IP/CIDR ranges. Add a temporary administrator IP only if needed for a separately authorized diagnostic; remove it afterward. [Atlas database users](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/), [network access lists](https://www.mongodb.com/docs/atlas/security/ip-access-list/)
3. Copy the Atlas Python driver SRV connection string into Render secrets. `pymongo[srv]` supplies DNS resolution; Atlas SRV uses TLS. Keep driver-recommended retry/write-concern options. MongoClient explicitly selects `MONGO_DB_NAME`, rather than relying on the URI's default database. [Atlas resilient connection guidance](https://www.mongodb.com/docs/atlas/resilient-application/)
4. Confirm the selected Atlas deployment exposes a replica set, logical sessions and transactions. A successful ping alone is insufficient. The staging initializer checks `hello` and a read-only transaction; its separately authorized initialization later commits staff accounts plus a readiness marker atomically. That commit must succeed before batch mode is enabled. [MongoDB transactions](https://www.mongodb.com/docs/manual/core/transactions/)
5. Do not change the local test suite to use Atlas. Automated record-changing regression tests remain locked to local **iraseth_test**. Actual Atlas connectivity, cluster-tier limits, indexes and transaction commit behavior still require post-provisioning verification.

**5. Exact first-deployment order — future authorized operation**

1. Review the complete current working tree, including unstaged and untracked application/brochure files. Cloud Git builds cannot see uncommitted local work. A later authorized snapshot must contain the required code, lockfiles, `docs/brochure/import-manifest.json`, assessment/review metadata, source PDF and referenced images. Never include `.env`, `.env.test`, credentials, dependencies or local database dumps. This preparation performs no commit or push. Do not use GitHub `main` as the staging source.
2. Obtain explicit authorization for creating the staging resources and deploying that reviewed source. Configure Render's source branch as `feature/storefront-modernization` and Auto-Deploy **Off**. For Vercel use two separate staging projects with the roots/build settings above; select the same reviewed feature-branch source before the first deployment. Check source branch/ref on every deployment screen. Do not accept an automatic initial build from `main`; if project creation cannot select the intended source, finish source/project configuration before triggering a build. Never change GitHub's default branch or main contents.
3. Provision Atlas as described above. Set all backend settings, with `BATCH_MODE=false` for the empty bootstrap. Use a Render web-service plan that supports SMTP on 587 and shell/one-off administration. Set Root Directory blank, language Python 3, build/start commands from section 1, and health-check path **`/api/ready`**. No database mutation command belongs in a build or automatic startup command.
4. Deploy the backend only when authorized. Startup creates application indexes in **staging**; this is expected schema preparation. Confirm `/api/health` and `/api/ready` return 200. At this stage the public catalog is empty and no staff accounts exist. Do not start operational UAT or add stock in legacy mode.
5. In the authorized Render shell/one-off process, from the **repository root**, first run the read-only initializer:

   ```sh
   python backend/tools/initialize_staging.py
   ```

   It must report that read-only checks passed, with no indexes/accounts/marker written. It refuses wrong environment/target, template accounts, non-replica-set targets and existing business/account records. It does not import Flask or run `ensure_indexes`. An existing nonempty staging database needs separate review; do not delete or reseed it to force this initializer to pass.

6. Only after the operator reviews that empty-staging result and is authorized to create the three configured staff accounts, run:

   ```sh
   python backend/tools/initialize_staging.py --apply --confirm-database iraseth_staging
   ```

   This creates the users/email index if needed, then atomically inserts three password-hashed staff accounts and the empty-inventory readiness marker. It creates **no products, batches, stock, orders, prices or brochure imports**. It refuses a second initialization rather than overwriting users. Do not run `backend/seed.py`: its product seeder deletes the product collection. Existing local migration/bootstrap scripts target localhost and must not be adapted by changing `.env` for this operation.

7. Set **`BATCH_MODE=true`** on Render and redeploy/restart the same reviewed source. Startup must pass the readiness marker and stock reconciliation guards. Confirm `/api/ready` again. Keep batch mode enabled for employee UAT; do not disable its guard to make a deployment turn green.
8. Configure the two Vercel staging projects with their actual API/staff URLs. Use Node 24.x and the committed lockfiles with `npm ci`. Keep Next output at framework defaults; never use `output: 'export'`, `next export` or `vite preview` as a cloud application server. The dashboard is a static Vite build, with all API calls going directly to Render. [Vercel monorepos](https://vercel.com/docs/monorepos), [Vite SPA routing](https://vercel.com/docs/frameworks/frontend/vite), [Vercel Node versions](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions)
9. Add the exact final frontend HTTPS origins to Render CORS settings and restart if they differ from the reserved aliases. Verify staff login, My Order, reference tracking, verified communication and `/support` reloads. Test both Preview URLs and staging aliases actually used; their hostnames can differ. Apply suitable staging access protection and search-engine exclusion. For Vercel deployment protection, ensure the intended UAT staff/customer test browser can reach both frontends; it must not turn required API requests into login HTML.
10. Complete the verification checklist below. The public catalog should honestly be empty until staff separately approve genuine product creation or staged test fixtures. An empty staging catalog is expected. Do not copy the three local products, fabricate stock/prices or import the 124 brochure candidates to populate it.

**6. API, CORS and authentication verification**

- Dashboard → Render uses cross-origin HTTPS with `Authorization: Bearer ...`; tokens stay in dashboard `sessionStorage`, are never put in URLs and remain subject to backend session/role checks. Cross-domain cookies are not required; Flask keeps `supports_credentials=False`.
- Verify preflight for `Authorization`, `Content-Type`, `Idempotency-Key` and `X-Support-Token`; allowed dashboard origins should receive `Access-Control-Allow-Origin` for that exact origin. An unrelated origin should not. Public endpoints remain public; CORS is not an authentication control.
- Storefront catalog renders server-side from Flask's `/api/public/products`; same-origin Next handlers proxy inquiry submission (`/api/quotations`) and tracking (`/api/tracking`). Employee JWTs never enter this public catalog path. Tracking must continue to expose only the reference/high-level recorded state.
- Next proxies deliberately do not trust browser-supplied forwarding headers. Their requests may share a Vercel egress IP/rate-limit bucket at Flask, including verification-code limits. Initial staging is a small pilot; expect 429/Retry-After during concentrated repeated UAT. Do not disable limits or blindly trust forwarded client headers. Trusted gateway identity would need separate design before higher traffic.
- Test Superadmin full access, Board Admin read-only and Sub-admin permitted operations through both UI controls and direct API requests. An anonymous private API request must fail; local UAT already checks direct Admin writes are forbidden.

Read-only command examples, after substituting the actual backend/dashboard origins:

```sh
curl -fsS https://REPLACE-BACKEND.onrender.com/api/health
curl -fsS https://REPLACE-BACKEND.onrender.com/api/ready
curl -fsS 'https://REPLACE-BACKEND.onrender.com/api/public/products?page=1&limit=1'
curl -i -X OPTIONS https://REPLACE-BACKEND.onrender.com/api/products \
  -H 'Origin: https://REPLACE-DASHBOARD.vercel.app' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: authorization,content-type,idempotency-key,x-support-token'
curl -i https://REPLACE-BACKEND.onrender.com/api/products
```

Expected: health `{"status":"ok"}`, readiness `{"status":"ready","database":"ok"}`, an empty public product list before real additions, allowed preflight headers, and 401 for the unauthenticated private catalog. Health/readiness do not prove SMTP delivery or a business transaction.

**7. Product images, brochure files and persistence**

Product uploads currently store validated PNG/JPEG/WebP **data URLs inside MongoDB product documents**. The canonical primary image and gallery are database data, not Render uploads or Vercel filesystem files. Existing limits are eight images per product, 200,000 decoded bytes each and 16 million pixels; animated/invalid images are refused. A Render restart/redeploy therefore preserves uploaded images while the Atlas database remains intact. Do not add a Render disk or object-storage integration merely to preserve the current uploads.

The local catalog currently has 127 records, including 124 PDF products; 11 PDF products have verified imagery and 113 retain placeholders. **Git transfers none of these MongoDB records or stored galleries.** The reviewed source includes original PDF/PNG media, manifests, approved WebPs and source evidence for future separately authorized work. An empty Atlas staging database will display an empty catalog until separately authorized product creation; do not copy local business data or run import tools automatically to populate it. Next brand assets are versioned under `storefront-next/public/brand/`.

Base64 and duplicated primary/gallery data increase BSON/response sizes. Validate `/products` with the intended image count/content and measure SSR responses before expanding staging: the current storefront fetches the whole public catalog and performs client-side filtering/pagination. Large image-heavy catalogs can exceed practical transfer/memory/function budgets. Vercel documents a 4.5 MB non-streamed Function request/response limit; streamed responses have a different response limit. This is a load-verification gate, not a claim that the current small catalog fails. A future object store/CDN and server-side catalog pagination need separate work and must preserve source/image approval controls. [Vercel payload limits](https://vercel.com/docs/functions/limitations)

Brochure PDFs/manifests/source PNGs must be included in the reviewed Render repository snapshot and remain protected by staff routes; they are not product imports. No runtime PDF extraction dependency is needed: `requirements-brochure.txt` is optional offline tooling. Keep source hashes unchanged. Products are not created just because those files are packaged.

Render's filesystem is ephemeral. `/tmp/iraseth-staging-backups` is scratch storage, not a durable backup. Use an appropriate Atlas backup/export policy for the chosen staging tier and document its recovery procedure before storing valuable test data. Do not rely on local backup endpoints for batch-mode persistence.

**8. Verified email requirements**

Use a genuine SMTP provider and verified sender/domain, with the provider's SPF/DKIM setup and any sandbox recipient verification completed. Configure `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, port **587** and `SMTP_USE_TLS=true`. The current mailer uses STARTTLS, not implicit SSL; port 465 is not a supported drop-in alternative. Never turn TLS off to work around a connection problem.

Render **free** web services block outbound ports 25, 465 and 587; all Render services block port 25. Free instances also spin down and can exceed the storefront's 12/20-second proxy deadlines while waking. Use a plan that supports the current SMTP flow and avoids idle spin-down for this staging UAT, or leave verified-email UAT blocked pending a separately scoped HTTPS mail-provider integration. No plan or mail service has been purchased/created here. [Render free-service limits](https://render.com/docs/free)

Verify an OTP arrives at an actual authorized staging mailbox, is accepted once, expires/rejects invalid attempts, and never appears in logs/screenshots. Verify staff status mail, an alternate address routed to review, and order-linked support OTP/chat. Provider acceptance is not inbox delivery; inspect the destination mailbox/spam folder. With SMTP absent/failing, preserve truthful failure messages. Local UAT used an in-memory mail double and cannot certify external delivery. Keep `EMAIL_ASYNC=false` initially; do not claim the existing background executor is a durable delivery guarantee.

**9. Post-deployment acceptance and rollback**

| Gate | Required observation |
| --- | --- |
| Source/target | Correct reviewed feature-branch ref; Render production safeguards + staging target; no `main`, localhost or production connection |
| Startup | Correct Python, dependencies and Gunicorn worker; full brochure paths available; no URI/password/token disclosure in logs |
| Database | Atlas ping, expected indexes including unique SKU comparison key, successful initializer transaction, then batch readiness at startup |
| Frontend wiring | HTTPS API calls, correct CORS/preflight, stable aliases, `/support` deep-link refresh and employee login link |
| Data | No copied local/customer records, products, stock or brochure imports from deployment/bootstrap; empty catalog handled honestly |
| Communications | Real authorized mailbox receives OTP/status messages; alternate verified email cannot receive private inquiry details |
| Functionality | Repeat the local UAT flow with separately authorized staging-only fixtures if record-changing cloud UAT is approved: product/images → inquiry → one Pending order → reserve → fulfill → invoice; no duplicate mutations |
| Persistence | Separately approved staging image survives API restart and frontend redeploy; test snapshot/recovery strategy known |
| RBAC/privacy | Admin mutation forbidden, anonymous private access forbidden, tracking minimal, staging protected appropriately |

Do not run the local automated suite against Atlas by editing its test guards. Cloud fixture creation, stock operations and SMTP messages are not performed by this preparation and require their own authorized staging verification. Read-only health checks are suitable immediately after deployment; stateful acceptance waits for that authorization.

On failure, stop further mutations. Roll back each app to the last reviewed compatible staging deployment/configuration while retaining Atlas data and idempotency keys. Do not run destructive seed/reset/restore commands, silently disable batch readiness, or retry a stock/import operation with a new key after an ambiguous response. The first deployment has no previous healthy release; keep it unavailable for operational UAT until its failing gate is resolved. Code rollback does not undo database writes or remove indexes. No brochure import is part of deployment or rollback.

**10. Local preparation verification and remaining gates**

- Backend: **215 passed, 1 deselected** in the completed recovery regression. The excluded test imports the actual 124 brochure candidates. Regression tests use isolated local `iraseth_test` only.
- Dashboard: build, existing 124-row CSV checks, API-origin guards, preflight headers and SPA configuration checks passed. Production dependency audit reported zero advisories.
- Storefront: production build, TypeScript check and all npm checks passed, including the new native PNG/WebP image-pipeline test. `npm audit --omit=dev` reports **zero advisories**, and `npm ls` reports a consistent tree. Linux x64/arm64 Sharp packages are present in the lockfile; actual Linux/Vercel runtime execution is still a post-provisioning gate.
- Browser: **15 scenarios passed** against isolated `iraseth_test`, including actual Next image optimization, gallery uploads/carousel, My Order, reference tracking, verified communications with a mail double, inquiry decisions, FEFO reservations/fulfillment, invoices, analytics, RBAC and brochure draft/dry-run safeguards. Dashboard requests reached the separate test Flask origin directly; ordinary local dashboard output was rebuilt afterward. See [browser evidence](staging/recovery-verification/browser-uat-results.json).
- The staging initializer was invoked with local development settings and correctly **refused before any database connection**. Its `--apply` path has not been run here. The pure target/password/emptiness guards and Gunicorn configuration are tested.
- Still required from the owner: real staging project/hostnames, chosen Render/Atlas service tiers, staging-only credentials, three genuine staff mappings/passwords, SMTP provider/sender/mailboxes, reviewed deployment source and later authorization to create/deploy services.
- Actual Atlas, SMTP, Render Linux/Gunicorn and Vercel runtime behavior remain unverified until resources are authorized and provisioned. Local Windows builds cannot certify Linux Gunicorn process startup; configuration and Flask behavior were checked locally.

Before/after comparisons matched all 18 checked iraseth_dev business/metadata collections, four index sets, existing Git staging and environment files. Browser fixture records were verified removed from iraseth_test. Previous UAT evidence under docs/uat was preserved; new recovery evidence is separate. No automatic deployment integration, cloud CLI login, cloud provisioning, actual brochure import, commit or push was used during this preparation/recovery.

The repository cleanup audit is separate from deployment preparation: see [legacy cleanup recommendations](LEGACY-CLEANUP-AUDIT.md). No legacy directory needs to be deleted for these three deployment targets. Do not run the old storefront build, which clears/replaces site/, as a staging verification command.
