# Repository cleanup report

Target: current local `feature/storefront-modernization` working tree. This is a bounded cleanup of proven obsolete files, not a retirement of unknown external static hosting. No commit, push, merge, deployment, Git reset/clean/restore/stash, backup folder or development-database write was performed.

## Exact removals and move

| Former path | Classification | Action and evidence |
| --- | --- | --- |
| `legacy-storefront/index.html` | SAFE TO REMOVE | Removed unchanged archived entrypoint. The archive explicitly declared itself replaced and safe to delete; its root-relative script paths did not work from that folder. No active app, old React build or hosting script referenced this file. Company About/Mission/Leadership/contact content remains in `storefront/src/pages/`; source imagery remains intact. |
| `legacy-storefront/main.js` | SAFE TO REMOVE | Removed unchanged archived catalog/cart logic. No incoming import, script load or build-copy reference targeted this path. Active ordering uses existing Next inquiry routes. |
| `legacy-storefront/README.txt` | SAFE TO REMOVE | Removed the two-line archive notice after recording its obsolete status here and in the pre-cleanup audit. No runtime/build consumers. |
| `DEVELOPMENT-PHASE1-3-README.md` | SAFE TO REMOVE from root; preserve content | Moved unchanged to `docs/history/DEVELOPMENT-PHASE1-3-README.md`. No existing incoming links were found. New documentation index links to the retained history. |

All three removed files and the moved document were tracked, unchanged relative to HEAD, and absent from the staged change set. No staged file was removed. The move preserved the exact file SHA-256; it was not a backup or duplicate copy. No directory was recursively removed and no active application source was deleted.

## Retained candidates and dependency evidence

The [per-file classification manifest](repository-cleanup-verification/dependency-classification.json) records every reviewed legacy file, existing documentation/evidence item and reviewed test/tool, including exact paths, retention actions and baseline hashes. Generated outputs are listed as patterns. These are the directory-level decisions:

| Path/group | Classification | Reason and next condition |
| --- | --- | --- |
| `backend/`, `frontend/`, `storefront-next/` | MUST KEEP | Current Flask/MongoDB API, Vite dashboard and Next storefront, with existing tests, lockfiles, fixtures, migration/import tools and deployment configurations. |
| `storefront/` | NEEDS MIGRATION | Old React application still has its own scripts and content provenance. Its `build` runs Vite with `outDir: '../site'` and `emptyOutDir: true`, then `scripts/copy-admin.mjs`. Old HashRouter URLs and dashboard links need formal retirement. No old build was run. |
| `site/`, including `static/`, copied admin/scripts/styles/assets | UNCERTAIN | Internally referenced generated output. No checked-in hosting configuration proves whether it remains published externally. Duplication with root files is not sufficient deletion evidence. |
| Root `admin.html` | NEEDS MIGRATION | Old React Header/Footer link here, and `copy-admin.mjs` copies it into `site/`. Retire those entrypoints together after confirming actual public and staff hostnames. |
| Root `js/admin.js`, `js/api.js`, `js/config.js`, `js/mock-backend.js` | MUST KEEP | Root/copied admin HTML loads these scripts; old build copies the full directory. |
| Root `css/styles.css` | MUST KEEP | Root admin loads it; old build copies the directory. |
| Root `assets/ceo.png`, `logo.png`, `logo-mark.png`, `iso_logo.png` | MUST KEEP | Old build copies these assets; root admin directly uses its logo. Next uses independent approved `public/brand/` images. No media was deduplicated or recompressed. |
| `legacy-storefront/data.js` | UNCERTAIN | Contains historical `fmtPHP`; root/copied admin expects missing `js/data.js` and calls `fmtPHP`. Preserve this evidence until that old dependency is retired or repaired separately. |
| `frontend/src/BrochureReview.tsx`, `brochure-review.css`, `brochure-mapping.ts` | MUST KEEP for now | Review screen is not mounted, but the active deployment test reads `BrochureReview.tsx`; its CSS/mapping imports and mapping tests remain. Removing a tested source merely because its screen is unmounted would expand this cleanup into workflow/test retirement. |
| `docs/brochure/`, `docs/pdf-products/`, image plans/candidates | MUST KEEP | Original PDF, media, CSV/JSON identities/review/import decisions and exact image paths are consumed by backend tooling/tests and browser fixtures. No product source metadata or source imagery was removed. |
| Deployment/UAT/history reports and successful test evidence | MUST KEEP | Indexed as current instructions versus historical evidence. Existing paths and approval history remain intact. |
| Earlier failed UAT screenshots/attempt artifacts | UNCERTAIN | Historical failure/comparison evidence, not interchangeable with successful final results. Retained pending an explicit evidence-retention decision; no claim that they are runtime dependencies. |
| `node_modules/`, `.venv/`, `.next/`, `dist/`, Python/test caches, `*.tsbuildinfo` | SAFE TO REMOVE only when regeneration is intended | Retained locally for current builds, preview and tests. Ignored and hidden from Explorer/search instead of deleting required local dependencies. Tracked legacy `site/` has its separate hosting hold. |
| `.env`, `.env.test`, application environment files and sanitized example templates | MUST KEEP | Secret files remain ignored and unchanged; sanitized examples remain reviewable. No settings were copied over local environments. |

Searches covered imports, script tags, file reads, build-copy sources, assets and deployment configurations across the three active apps and the retained old pipeline. The 20 generated Next file traces contain no runtime dependency on `storefront/`, `legacy-storefront/`, `site/` or root `js/`, `css/`, `assets/`. Dashboard built asset URLs resolve, and all approved Next brand files exist. Backend Gunicorn still changes into `backend/` with repository-root source available; it does not serve root `site/` or admin files. The Vercel projects still build only their own application roots.

## Organization and exact configuration/documentation changes

- `.gitignore`: ignore `.next/` and `.vercel/` throughout the repository; replace blanket `.vscode/` exclusion with `.vscode/*` plus a narrow exception for `settings.json`. Real environment files/dependencies remain ignored. No existing tracked file was untracked.
- `.vscode/settings.json`: preserve `python.terminal.useEnvFile`; add Explorer/search exclusions for `node_modules`, `.next`, `dist`, `__pycache__`, `.pytest_cache`, `.venv` and TypeScript build metadata. Local files remain on disk.
- `README.md`: identify the active three apps and hosts, correct the storefront directory, link current verification/deployment guidance and explain retained legacy dependencies.
- `docs/README.md`: consolidate navigation to essential instructions and distinguish historical approval/evidence from current actions. Existing deployment/UAT instructions were not deleted or merged destructively.
- `docs/GITHUB-REVIEW-CHECKLIST.md`: replace obsolete old-storefront build instruction with the active checks, isolated test guard and browser UAT procedure; clarify secret/example handling.
- `docs/LEGACY-CLEANUP-AUDIT.md`: add a historical-state note linking this final report; preserve original dependency evidence.
- This report and `docs/repository-cleanup-verification/`: add exact classification, preservation and new UAT evidence.

No application API, schema, feature, dependency version, deployment command, public asset URL or production script was changed in this cleanup. Git's unstaged diff still includes earlier development work; it must not be attributed to this task. Exact task-relative paths and full-tree/staged diff summaries are recorded in the final preservation artifact. New untracked files do not appear in ordinary `git diff --stat`.

## Verification

- Backend: **232 passed, 1 deselected**, 155.64 seconds, local `iraseth_test`. The excluded historical bulk test simulates genuine staff SKU mappings; existing provisional identity, real source/gallery, inventory/order/invoice, rollback and RBAC coverage remained enabled.
- Dashboard: staff CSV/mapping checks, deployment/API-origin checks, TypeScript and Vite production build passed.
- Storefront: TypeScript, all `npm test` checks and production build passed. Checks include pagination, image/gallery interactions, native Sharp processing, inquiry retries, tracking proxy and deployment-origin guards.
- Browser UAT: **17 scenarios passed; zero issues or browser runtime errors**. Covered create/edit, actual Alpha Care uploads, existing-product PDF metadata/identity gates and receipt, employee/catalog pagination, categories/brand/stock filters, native image optimization, modal/shared URLs, My Order, tracking, verified communications, inquiry acceptance/decline, official approval/reservations, FEFO fulfillment, chat, invoices, manual-order cancellation, analytics and staff RBAC. See the completed [browser results](repository-cleanup-verification/browser-uat-results.json).
- Final fingerprints: **all 27 development collections and every index definition unchanged**, including all **127 complete product records**, stock, prices, orders, invoices, users and historical/image audits. No development login/session/stock mutation occurred. Git staging is identical across all 56 staged paths; environment files and unrelated local source are unchanged. Browser fixture product cleanup left zero `PYTEST-BROWSER-` records. See [preservation evidence](repository-cleanup-verification/preservation.json).
- Restored live preview: GET-only API pages returned **100 + 27 unique products**; all three updated image products passed live cards/modals, four image byte hashes, Out of Stock, Price Upon Request and disabled ordering checks. No browser errors. The one restored Next preview uses the existing Flask API on port 5000.
- Asset checks: 20 Next build traces checked, no legacy runtime dependency; built dashboard JS/CSS URLs and Next brand assets exist; VS Code JSON is valid; real environment files remain ignored. Normal `git diff --check` passed.

PowerShell initially selected blocked `npm.ps1`; checks were rerun with `npm.cmd`. The sandbox also blocked esbuild configuration discovery; the approved local rerun passed. Existing duplicate Next dev/preview servers shared `.next`; verified repository processes were stopped before the build. One preview is restored after UAT. These were execution-environment issues; no application fix was needed.

## Final structure and staging readiness

```text
backend/                 active API, tests, tools and migrations
frontend/                active employee dashboard
storefront-next/         active public storefront
docs/                    current index, deployment/UAT, source/evidence, history
.vscode/settings.json    generated-folder visibility only
README.md                current project entrypoint
.gitignore               secrets, dependencies and generated outputs

storefront/              retained legacy pipeline; migration hold
site/                    retained legacy output; hosting ownership hold
admin.html, js/, css/    retained connected legacy admin
assets/                  retained required legacy copy inputs
legacy-storefront/       data.js only; old admin dependency evidence
```

Local verification supports a separately authorized staging deployment using the existing [exact deployment plan](STAGING-DEPLOYMENT-PLAN.md). No cloud services were provisioned or deployed. Actual Atlas transactions/access, provider secrets/CORS, persistent image behavior, external SMTP, DNS/static-host ownership, content/image publication approval and stakeholder UAT still require staging verification. Provisional PDF identities and 113 source-image placeholders remain documented product-data limitations, not cleanup regressions.

The complete working source remains largely uncommitted, including required untracked application files. The preserved index is an earlier partial snapshot, not a deployable release by itself. Review the full working tree before any separately authorized GitHub operation. Do not deploy the old pipeline or use GitHub main as a side effect of this cleanup. Removing the connected legacy group later requires confirmation of publishing roots, URL/bookmark retirement and asset consumers; no whole-directory removal was attempted here.
