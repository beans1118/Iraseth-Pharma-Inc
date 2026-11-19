# Company developer setup verification

Verified 19 November 2026. The official Windows handover is [DEVELOPER-SETUP.md](../DEVELOPER-SETUP.md). The source and test evidence were reviewed on `main` for a local handover commit. No push or deployment was performed.

## Result

The PowerShell setup, standalone catalog/environment tools, backend fallback and sanitized local template now default to **`iraseth`**. No developer name or personal database suffix is required. Explicit `iraseth_local_<purpose>` overrides remain available for local sandboxes. Existing environment files are preserved; conflicting configured backend/shell targets stop setup instead of silently switching databases.

The supported applications remain Flask on 5000, the React employee dashboard on 5173 and the Next.js storefront on 3000. Both clients use the configured Flask API and the same MongoDB `products` collection. API origins and exact first-time/subsequent-run/account/start/stop/test/troubleshooting commands are in the guide.

A fresh eligible database receives exactly **124 reviewed brochure products**, **11 verified galleries / 12 images**, and no operational/customer data. The remaining 113 products retain placeholders. Product reconstruction and its content fingerprint are unchanged: the existing brochure service validates the reviewed selections and candidate-specific duplicate reviews, the existing product service inserts them, and completed gallery evidence/hashes validate the images. Next.js contains no hardcoded catalog.

Provisional SKU/unit restrictions remain unchanged: empty genuine SKU, pending unit, zero quantity/baseline, null internal/public price, Out of Stock / Price Upon Request and disabled ordering. Setup creates no stock, orders, invoices, staff accounts or customer records. Catalog records, setup audits and zero-stock batch readiness commit atomically; failure rolls back every record. Transactions and inventory safeguards remain enabled.

Complete Git source records for original products `MED-001`, `MED-002` and `SMP-001` remain unavailable. These records are not fabricated. All original products and existing business records are preserved wherever they already exist; any occupied eligible database is skipped rather than merged into or overwritten.

## Existing database compatibility

`-Database iraseth_dev -Status` reports the existing development target using its existing configuration. Even `-Apply` returns **`legacy-read-only`** and performs no import, index creation, readiness change or audit write there, including when it is empty. It is neither renamed nor migrated. A fresh official environment uses `iraseth`; another working environment can remain in a separate checkout.

`-Status` is read-only and avoids dependency/env changes. Ordinary setup prepares missing environments/dependencies and previews the database operation; `-Apply` is explicit. Repeated apply reports `already-initialized` with `created: 0`. Other preexisting data reports `existing-data-skipped`, with no changes to products, staff edits, stock, orders, historical audits or indexes. Dangerous database names, remote/credentialed MongoDB endpoints and unsafe URI options remain refused.

## Files changed for this handover

| File | Purpose |
| --- | --- |
| `DEVELOPER-SETUP.md` | Renamed the previous personal setup guide; generic installation, `iraseth` defaults, existing-database compatibility, exact PowerShell commands and troubleshooting. |
| `scripts/setup-local.ps1` | Optional database parameter defaults to `iraseth`; updated handover link and preserved preview/status/apply behavior. |
| `backend/tools/setup_local_catalog.py` | Shared default database/URI constants, approved explicit sandbox names and unconditional read-only legacy reporting; source/import/gallery workflow retained. |
| `backend/tools/configure_local.py` | Generic CLI defaults; prevents creating a new environment against the legacy database without its existing configuration. Preserves private files and effective client settings. |
| `backend/tools/create_local_test_accounts.py` | Accepts the official default database in the existing interactive, non-overwriting bootstrap. |
| `backend/config.py`, `backend/.env.example` | Local database defaults to `iraseth`; sanitized template uses rs0, batch mode and current client CORS origins. Actual `.env` files were not changed. |
| `backend/utils/test_configuration.py` | Shared strict test configuration for the explicitly selected disposable endpoint; does not load a private environment file in disposable mode. |
| `backend/tests/conftest.py`, `backend/tools/add_pdf_products.py`, `backend/.env.test.example` | Regression runner and brochure test subprocess share the opt-in isolated port. Existing guarded legacy test mode remains compatible. |
| `backend/local_setup_tests/test_setup_local.py` | Generic examples and coverage of default/override targets, read-only legacy behavior and disposable-test configuration. |
| `frontend/vite.config.ts` | Reads the configured Vite development API target from dotenv as well as the shell. |
| `storefront-next/lib/catalog.ts`, `storefront-next/components/CatalogClient.tsx` | Distinguish configuration/connection/API/response failures from valid empty and filtered catalogs, with bounded requests. |
| `storefront-next/tests/catalog-errors.mjs`, `storefront-next/tests/catalog-pagination.mjs` | Verify catalog error/empty states, rendering signals and API pagination. |
| Root/backend/frontend/storefront READMEs, `docs/README.md` | Updated company guide links, generic defaults and safe test instructions. |
| `docs/LOCAL-SETUP-REPORT.md` | Current handover scope and verification evidence. |

The handover includes the Vite dotenv proxy fix and distinct storefront catalog failure/empty states reviewed alongside the setup tools. No approved source PDF, manifest, image asset, product validation rule or transaction safeguard was changed. Real environment files, credentials, dependencies, builds, database files, browser screenshots and raw fingerprints remain ignored by Git.

## Validation

Tests used a **separate disposable local rs0 on 127.0.0.1:27028**, with files under ignored `test-results/company-handover/`. The default name **`iraseth`** was tested on that instance, not on the existing MongoDB server. New private env files were created only in a sanitized source copy; dependency inputs were unchanged and verified installed dependencies were reused. Client builds used that copy to avoid sharing generated Next output with a running development server.

| Check | Result |
| --- | --- |
| Backend regression | **233 passed**, no deselections. Ran the actual working source with `IRASETH_TEST_MONGO_PORT=27028`; no source-copy port substitutions or original test database writes. |
| Setup safety suite | **30 passed**: default/legacy/sandbox targets; unsafe-target refusal; env preservation/no shadowing; shell conflicts; real source reconstruction; empty API; pagination/private-public identity; read-only preview; repeat apply; occupied data; rollback; isolated regression settings. |
| PowerShell default preview/apply | Omitting `-Database` selected `iraseth`, previewed 124 products/11 galleries without writes and then initialized exactly 124 records on explicit apply. |
| Repeat apply/status | **0 new records**. Every private env byte, catalog document, setup audit and index definition matched its pre-repeat fingerprint. |
| Existing legacy status | Actual `iraseth_dev` reported **128 products**, `legacy-read-only`, `created: 0`. All preexisting records, including the original three, remained intact. |
| Dashboard | Brochure/deployment checks and TypeScript/Vite build passed. |
| Storefront | Entire `npm test`, typecheck and Next.js production build passed. |
| Browser integration | Real local Chrome login through Vite's dotenv proxy; all **124 employee/API/storefront product IDs matched** on the default database. |
| Pagination | API **100 + 24**; storefront **24/24/24/24/24/4**. No missing or duplicate IDs. |
| Images and product restrictions | All **12 images on 11 product detail pages** decoded; employee and public galleries, underpad second image, search/category filtering, pending-identity notice, zero availability, null public prices and disabled ordering passed. |
| Empty/error UI | A genuine empty MongoDB public catalog displayed **No products published yet**; stopping the isolated backend displayed its connection-error message. Nonmatching search displayed **No matching products found**. No browser runtime errors. |
| PowerShell parser / Git whitespace | Passed. |
| Original database preservation | Every document and index in all **27 `iraseth_dev` collections** matched the starting fingerprint, including **128 existing products**, stock, orders, users and audits. Every document/index in all **26 original `iraseth_test` collections** also matched. |

Test application processes and the disposable MongoDB were stopped after verification. Disposable data was retained rather than deleted. Current verification introduced no additions to the existing development database. Raw browser results, screenshots and fingerprints remain in ignored `test-results/company-handover/`.

## Exact setup commands

After installing prerequisites and saving local work, from the repository root:

```powershell
git switch main
git pull origin main
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1
# Review the preview, then:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1 -SkipDependencies -Apply
# Read-only status on later runs:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-local.ps1 -Status
```

Use [DEVELOPER-SETUP.md](../DEVELOPER-SETUP.md) for the exact account bootstrap and three application startup commands, isolated MongoDB/test commands, stop instructions and API diagnostics. Existing environment files must already match the selected target, or be deliberately configured by their owner; setup never overwrites them. Local MongoDB/rs0, Python/Node, downloaded dependencies, private passwords/SMTP configuration, authoritative supplier SKU/unit evidence and unavailable product-specific images remain local requirements. Git alone cannot supply missing original product records or operational inventory.


## Final local commit review

The final review fetched `origin` and confirmed that `main` matched `origin/main` before the local commit, with no unresolved merge entries or preexisting staged files. All 23 changed/new source files were reviewed. Private environment files, local database files/exports, generated builds/dependencies, screenshots and raw test records remain excluded. Candidate content was checked for known private environment secrets and credential/key/token patterns; only sanitized template placeholders and synthetic test values are included. The official setup defaults to `iraseth` and contains no personal developer names or machine paths.

Final relevant checks passed again: **233 backend tests**, **30 setup safety tests**, dashboard brochure/deployment checks and build, storefront tests/typecheck/build, and the setup script plus **13 documented PowerShell command blocks** parsed without errors. Default preview/apply reconstructed 124 provisional zero-stock/unpriced products on a newly created disposable MongoDB instance. Repeat apply/status preserved every environment byte, catalog/audit document and index. All documents and indexes in the existing development and test instances matched the final review's starting fingerprints. No existing database was changed.

Final regression artifacts remain ignored under `test-results/final-setup-commit/`. The browser findings above are from the preceding handover verification; this final review reran the full backend/setup/client regression suites and production builds. No push or deployment is part of the local commit operation.

Reviewed commit contents (23 files):

- `DEVELOPER-SETUP.md`
- `README.md`
- `backend/.env.example`
- `backend/.env.test.example`
- `backend/README.md`
- `backend/config.py`
- `backend/local_setup_tests/test_setup_local.py`
- `backend/tests/conftest.py`
- `backend/tools/add_pdf_products.py`
- `backend/tools/configure_local.py`
- `backend/tools/create_local_test_accounts.py`
- `backend/tools/setup_local_catalog.py`
- `backend/utils/test_configuration.py`
- `docs/LOCAL-SETUP-REPORT.md`
- `docs/README.md`
- `frontend/README.md`
- `frontend/vite.config.ts`
- `scripts/setup-local.ps1`
- `storefront-next/README.md`
- `storefront-next/components/CatalogClient.tsx`
- `storefront-next/lib/catalog.ts`
- `storefront-next/tests/catalog-errors.mjs`
- `storefront-next/tests/catalog-pagination.mjs`
