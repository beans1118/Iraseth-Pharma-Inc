# Interrupted-task recovery — 16 November 2026

Current branch: `feature/storefront-modernization`. Recovery is complete for the confirmed dependency/image-pipeline issues. **215 backend tests and 15 browser scenarios passed; both application builds and their requested checks passed.** No application feature or image-storage redesign was introduced. Staging still needs actual service settings, credentials and authorized cloud verification.

**Recovered state**

Before changing files, staged, unstaged and untracked work was inspected. The original staging diff remains 56 files, 2,991 insertions and one deletion, with the same binary-diff SHA-256 as before staging preparation. Existing inventory/order/inquiry/gallery/tracking/brochure work was retained.

Already completed before the interruption:

- Next.js 15.3.3 → 15.5.29 and React/React DOM 19.1.0 → 19.1.10 were installed, built and checked successfully.
- Render Gunicorn/dependency settings, Vercel SPA/Next build configuration, frontend API-origin wiring, staging environment templates, staging target/secret guards and a read-only-by-default Atlas initializer were prepared. They were not deployed or applied to Atlas.
- Earlier backend regression had passed 212 tests, with the real 124-source import test excluded; three additional staging-guard tests subsequently passed in the dedicated configuration run. Dashboard and storefront checks had also passed before the transitive dependency changes.
- The production audit still reported the nested PostCSS and Sharp issues. `package.json` had the proposed fixes, but the package installation was **not executed** because automatic approval review hit the usage limit. That left the manifest, lockfile and installed packages inconsistent.

**Completed fixes and current versions**

| Dependency | State at recovery | Final state |
| --- | --- | --- |
| Next.js | 15.5.29 installed | **15.5.29**, retained |
| Storefront React / React DOM | 19.1.10 installed | **19.1.10**, retained |
| Root PostCSS | 8.5.32 installed, pending manifest requested 8.5.23 | **8.5.32**, pinned to retain the already installed patched version |
| Nested Next PostCSS | Vulnerable 8.4.31 | **8.5.32**, deduplicated through `postcss: "$postcss"` override |
| Sharp | Vulnerable 0.34.5 | **0.35.5**, targeted override with matching native packages |
| Dashboard React / React DOM | 19.3.1 installed | Retained; no dashboard dependency upgrade |
| Dashboard Vite | 6.4.5 installed | Retained |

The existing Next.js major version was retained; no forced audit upgrade to Next.js 16 was performed. Sharp's Node requirement is >=20.9.0, satisfied by the tested local Node 24.13.1 and the planned Vercel Node 24.x setting. The lockfile includes Sharp 0.35.5 Linux x64/arm64 packages and Linux x64 libvips 1.3.4. Actual Vercel/Linux runtime startup remains unverified.

After installation, `npm ls next react react-dom postcss sharp --all` succeeded without unmet/invalid entries. `npm audit --omit=dev --json` reported **zero production advisories**. This is the npm audit result for the resolved production tree, not a claim that every possible application or backend security issue has been audited.

The slow native-package download was completed using bounded byte ranges from the official npm registry and checked against its official SHA-512 before caching. No registry configuration was changed. Temporary package-download artifacts were removed; no project backup or source copy was created.

**Image verification**

- The new native contract check reads the three existing brand PNGs, resizes them in memory and re-encodes PNG/WebP through Sharp 0.35.5. All six conversions decoded with valid dimensions/formats. No source asset was modified.
- The browser exercised the actual `/_next/image` endpoint, received HTTP 200 with `image/webp`, verified the RIFF/WEBP signature and confirmed the logo decoded in the browser.
- Product create/edit, two-file PNG gallery uploads, primary-image reorder, arrows/thumbnails/keyboard, standalone detail URL and disabled add for out-of-stock products passed.
- Product images remain validated data URLs persisted in MongoDB. Existing limits remain eight images, 200,000 decoded bytes per image and 16 million pixels. No filesystem upload path or object-storage service was introduced.
- The old and Next CEO PNG files have different packaging bytes, but identical decoded RGBA pixels. They were not recompressed or replaced.

**Verification results**

| Check | Result |
| --- | --- |
| Backend full regression, isolated local iraseth_test | **215 passed, 1 deselected**, 133.79 seconds |
| React dashboard | TypeScript (`tsc -b`) and Vite build passed; CSV and deployment-configuration checks passed |
| Dashboard cross-origin mode | Built with temporary test API origin 5011; browser confirmed direct API calls from dashboard origin 5174 |
| Ordinary dashboard output | Rebuilt afterward without temporary API settings, restoring local proxy behavior |
| Next production build | Passed on 15.5.29 after final overrides |
| Next TypeScript and npm checks | Passed, including gallery, catalog pagination/errors, native image processing, tracking proxy, deployment guards and inquiry retries |
| Storefront production dependency audit | Zero advisories; installed dependency tree consistent |
| Browser UAT | **15/15 passed**, zero browser runtime errors; desktop and 390-pixel mobile emulation |
| Development-data preservation | All 18 checked business/metadata collections and four index sets unchanged |
| Repository preservation | Existing staged diff and all environment-file hashes unchanged; no pre-existing source file deleted |

The intentionally deselected backend test is `test_actual_124_clear_sources_approve_without_inventory_or_price_changes`, because this task does not authorize importing actual brochure candidates. Synthetic transaction/approval fixtures remain covered. The older `test:browser` script that imports a PDF candidate was not run; the no-import local UAT runner was used.

Browser coverage included one linked Pending order on inquiry acceptance, no stock change on submission/acceptance/decline, exact FEFO reservations on approval, fulfillment deduction/release, manual cancellation, invoices without stock mutation, analytics, read-only Admin rejection, Superadmin void, verified customer ownership isolation and order-linked support chat. SMTP delivery used an explicitly isolated in-memory mail double; no real mail was sent.

Evidence: [browser results](staging/recovery-verification/browser-uat-results.json), [mobile capture](staging/recovery-verification/mobile-uat.png). Existing reports/screenshots under `docs/uat/` were preserved.

Reproduction commands, using the existing guarded local test configuration:

```powershell
# backend/
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -k "not test_actual_124_clear_sources_approve_without_inventory_or_price_changes"

# frontend/ — ordinary build and pure checks
npm.cmd run build
npm.cmd run test:brochure
npm.cmd run test:deployment

# storefront-next/
npm.cmd run build
npm.cmd run typecheck
npm.cmd test
npm.cmd audit --omit=dev
```

For the staging-style browser run, first build `frontend/` with `VITE_API_BASE_URL=http://127.0.0.1:5011` set **only in that build process**. Then in `storefront-next/`, run `node tests/local-uat.mjs` with process-only `LOCAL_UAT_DIRECT_API=1` and `LOCAL_UAT_OUTPUT_DIR=docs/staging/recovery-verification`. Remove those temporary process variables and rebuild the ordinary dashboard afterward. Do not edit `.env`/`.env.test` or point the runner at Atlas/iraseth_dev. The runner starts temporary ports 5011/3101/5174 and cleans only its own fixtures.

**Exact files changed during this resumed task**

Modified existing files:

- `storefront-next/package.json`: retain patched PostCSS 8.5.32, keep the pending targeted overrides and include the native image-pipeline check in npm tests.
- `storefront-next/package-lock.json`: synchronize the final resolved PostCSS/Sharp tree and native platform packages.
- `storefront-next/tests/local-uat.mjs`: add the real Next image-optimizer browser check.
- `docs/STAGING-DEPLOYMENT-PLAN.md`: replace interrupted/pending status with final versions, completed verification and preserved-state evidence.

Added files:

- `storefront-next/tests/image-pipeline.mjs`
- `docs/LEGACY-CLEANUP-AUDIT.md`
- `docs/RECOVERY-VERIFICATION-REPORT.md`
- `docs/staging/recovery-verification/browser-uat-results.json`
- `docs/staging/recovery-verification/mobile-uat.png`

All previously prepared Render/Vercel/configuration source changes remain in the working tree and were not reimplemented. No legacy application source, image, stock service, inquiry conversion, invoice or RBAC implementation was edited in this recovery.

**Cleanup recommendations and remaining issues**

[Exact legacy classification and evidence](LEGACY-CLEANUP-AUDIT.md) are recorded separately. No whole legacy folder is unconditionally cleared for deletion. `legacy-storefront/index.html`, `main.js` and `README.txt` are unreferenced archive removal candidates; `legacy-storefront/data.js` has a review hold because the old admin still expects a missing `js/data.js` and uses its `fmtPHP` function. The old React build depends on root admin/scripts/styles/assets and clears/rebuilds `site/`; `site/` hosting ownership is unverified. No legacy build or deletion was performed.

The current desktop product dialog's upper-left alignment remains a previously reported cosmetic item; it does not block tested controls. Existing image-heavy whole-catalog transfer/SSR limits still need load verification before expanding the catalog. No speculative storage or UI redesign was added.

**Staging readiness**

The confirmed local dependency/image blockers are resolved, and the [staging deployment plan](STAGING-DEPLOYMENT-PLAN.md) is current. The repository is prepared for a later authorized staging setup, subject to real Render/Vercel hostnames, isolated Atlas credentials/network access/transaction verification, genuine staff accounts and readiness initialization, and a working SMTP provider/sender/mailbox. Render must support the existing SMTP flow; free-service SMTP restrictions remain relevant. Actual Atlas, SMTP, Linux Gunicorn and Vercel deployment execution have not been certified locally.

Before/after fingerprints confirmed iraseth_dev data/indexes, all environment files and Git staging were unchanged. Browser fixture products, inquiries, orders, invoices, batches, reservations, movements, catalog events, users and customer support sessions were verified absent after cleanup. Normal test rate-limit counters expire through their existing TTL policy. No actual brochure candidates were imported. No reset, restore, clean, stash, source deletion, commit, push, merge, cloud service creation or deployment was performed; GitHub main was not changed.
