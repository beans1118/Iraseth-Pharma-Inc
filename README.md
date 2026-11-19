# Iraseth Pharma

The current system uses a Flask/MongoDB API, a React employee dashboard and a Next.js public storefront.

| Directory | Purpose | Planned staging host |
| --- | --- | --- |
| `backend/` | API, authentication, inventory, inquiries, orders, invoices, analytics and tests | Render |
| `frontend/` | Employee dashboard: React, TypeScript and Vite | Vercel |
| `storefront-next/` | Public Products, My Order and reference tracking: Next.js | Vercel |
| `docs/` | Deployment/UAT instructions, product source evidence, import metadata and reports | Brochure files are required by backend tools |

## Local development

For a fresh clone, follow [the company developer setup](DEVELOPER-SETUP.md). It installs dependencies and safely reconstructs the 124 approved brochure products in the default local `iraseth` database, with explicit local overrides supported. Git does not transfer MongoDB records; the 3 original products cannot be reconstructed from committed placeholders. Setup has a database dry run and never overwrites existing data.

Use Python 3.12, Node.js 24 and local MongoDB with replica set `rs0`. Keep existing environment files private; example files document settings. See each application's README and [the documentation index](docs/README.md).

From `backend/`, with its virtual environment activated:

```powershell
python app.py
```

From `frontend/`:

```powershell
npm.cmd ci
npm.cmd run dev
```

From `storefront-next/`:

```powershell
npm.cmd ci
npm.cmd run dev
```

The dashboard's default Vite port is 5173 and Next.js uses 3000. Review configured API origins before running. These commands do not initialize or seed a database.

## Verification and data safety

Automated record-changing tests use `iraseth_test` on a separate disposable MongoDB instance. Follow the developer guide and set `IRASETH_TEST_MONGO_PORT=27028`; the backend verifies the actual test endpoint. Do not seed, migrate or import into `iraseth_dev` as a test setup. Product creation does not add stock: receiving uses batches, and provisional PDF identities block stock operations until genuine SKU and unit confirmation.

Run the [current verification procedure](docs/GITHUB-REVIEW-CHECKLIST.md). Latest cleanup results and exact retained legacy dependencies are in [the repository cleanup report](docs/REPOSITORY-CLEANUP-REPORT.md). Build checks do not establish external SMTP delivery or cloud readiness by themselves.

## Deployment and retained legacy files

Follow [the staging deployment plan](docs/STAGING-DEPLOYMENT-PLAN.md) for the Render root/start command, separate Vercel project roots, isolated Atlas database, secrets, SMTP and health checks. Deployment, provisioning, commits and pushes require separate authorization.

`storefront/` is the old React app, not the active customer storefront. Its build clears/recreates `site/` and copies root `admin.html`, `js/`, `css/` and `assets/`. That connected legacy group remains until static-host ownership and URL retirement are resolved. Do not run its build or select those folders as the new deployment roots. `legacy-storefront/data.js` remains for the unresolved old admin dependency. Company-source content and imagery are retained.

Superadmin and Sub-admin writes remain subject to backend permissions and stock safeguards; Board Admin is read-only. Stakeholder UAT and permissions sign-off remain required before production.
