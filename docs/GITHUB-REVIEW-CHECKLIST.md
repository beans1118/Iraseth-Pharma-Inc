# GitHub review preparation

## Before committing

1. Make sure Phase 6 receiving and Phase 7 RBAC tests still pass.
2. Run `npm run build` in `frontend/` and `storefront/` (verify storefront build output first).
3. Run `python -m pytest tests/ -v` in `backend/`.
4. Run `git status --short` and `git diff --check`.
5. Use `git ls-files` to identify already tracked private/generated files: `.gitignore` does **not** retroactively untrack them.
6. Inspect the staged file list: `git diff --cached --name-only` and `git diff --cached --stat`.
7. Never commit credentials, `.env*`, database dumps, private customer exports, virtual environments, or `node_modules`. If secrets were previously committed, review rotation and history remediation rather than simply deleting the current file.
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

Old `site/`, `admin.html`, `js/`, `css/`, and `legacy-storefront/` may still be used by static hosting or development workflows. Verify deployment references before archiving or removing them. Keep automated tests; phase-specific filenames can be renamed later as a separate refactor.
