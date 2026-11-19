# GitHub review preparation

## Before committing

1. Make sure Phase 6 receiving and Phase 7 RBAC tests still pass.
2. In `frontend/`, run `npm run test:brochure`, `npm run test:deployment` and `npm run build` (includes TypeScript). In `storefront-next/`, run `npm run typecheck`, `npm test` and `npm run build`. Do not build legacy `storefront/`; it overwrites `site/`.
3. In `backend/`, install `requirements-dev.txt` in the local virtual environment. If `.env.test` is absent, create it from the sanitized `.env.test.example` without overwriting an existing file. Run `.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider`. The test configuration enforces local `iraseth_test`. All 233 tests now pass, including the historical bulk mapping simulation with disposable identities; this does not approve live SKU/unit mappings. Never point tests at `iraseth_dev` or Atlas.
4. Run `git status --short` and `git diff --check`.
5. Use `git ls-files` to identify already tracked private/generated files: `.gitignore` does **not** retroactively untrack them.
6. Inspect the staged file list: `git diff --cached --name-only` and `git diff --cached --stat`.
7. Never commit real `.env`/`.env.*` secrets, database dumps, private customer exports, virtual environments, generated builds or `node_modules`. Sanitized `*.env.example` / `.env.example` templates are intended documentation. If secrets were previously committed, review rotation and history remediation rather than simply deleting the current file.
8. Commit to a review branch; do not push or merge to `main` without explicit owner approval.

## Manual RBAC tests — assigned to Mark

- [ ] Superadmin: account management and permitted operations
- [ ] Admin: view products/inventory/orders/invoices/reports; verify all writes are blocked by API, not just hidden in UI
- [ ] Sub-Admin: add/edit products, receive/release stock, fulfill orders
- [ ] Sub-Admin: cannot delete catalog products or manage users
- [ ] Invoice create/issue/void and support messaging permissions approved by stakeholders and verified
- [ ] Record any confusing UI wording, accessibility or layout problems, and endpoint responses

Do not mark user acceptance complete until Mark reports the results.

## Do not delete blindly

Old `storefront/`, `site/`, `admin.html`, `js/`, `css/`, `assets/` and remaining `legacy-storefront/data.js` have retained dependency/hosting holds. See [the cleanup report](REPOSITORY-CLEANUP-REPORT.md) for exact classifications. Keep automated tests, migration tools, source media and review metadata.

For browser UAT, first finish both production builds with no other Next process using the same `.next` directory. From `storefront-next/` in PowerShell:

```powershell
$env:LOCAL_UAT_OUTPUT_DIR='docs/repository-cleanup-verification'
$env:LOCAL_UAT_PDF_PRODUCTS='1'
$env:LOCAL_UAT_IMAGE_CANDIDATES='1'
node tests/local-uat.mjs
```

The browser runner starts disposable services on ports 5011/5174/3101 and hard-locks writes to local `iraseth_test`. PDF fixture identity confirmation is simulated only in that database. It uses an in-memory test mailbox; external SMTP requires a separate staging check. The runner cleans only its own fixture records. Stop its servers before rebuilding Next.js. Review logs and screenshots before marking UAT complete; stakeholder sign-off is still required.
