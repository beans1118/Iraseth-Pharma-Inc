# Final local UAT — 16 November 2026

Branch: `feature/storefront-modernization`. Feature development paused. **201 backend tests and all 14 browser scenarios passed.** Dashboard and storefront builds/checks passed. One functional UI defect was fixed and retested. A minor desktop layout inconsistency remains. Live SMTP delivery is blocked by missing configuration.

All automated record changes used **iraseth_test** on the local MongoDB replica set. No actual brochure candidates were imported, including into the test database. The positive 124-source import test and the older browser suite that imports a brochure product were deliberately excluded. Synthetic brochure validation/transaction tests remain in the backend suite.

**Functionality results**

| Area | Result and evidence |
| --- | --- |
| Product creation/editing | Browser pass: required identity/category/unit, description, feature and specification; new item starts at zero stock without a batch. Metadata editing preserves stock. |
| Image uploads/gallery | Browser pass: two actual PNG file uploads, primary-image reordering, three-image carousel arrows/thumbnails/keyboard, initial close-button focus and standalone product URL. Upload validation also passes backend regressions. |
| Public catalog | Browser pass: live Flask data through Next.js, search, real category/brand/availability filters, pagination across 105 matching products, out-of-stock detail and disabled add button, Price Upon Request. |
| My Order inquiry | Browser pass: add from product modal, quantity changes, actual form submission and RFQ success reference; exactly one inquiry with quantity 3; no reservation or stock deduction. Retry/idempotency checks also pass. |
| Reference-only tracking | Browser pass: reference alone shows recorded status/milestones without customer identity, email form or private details in the basic result. Observed New, In Review, Pending, Declined, Approved and Fulfilled transitions. Backend tests cover malformed/missing references and private-field exclusion. |
| Verified communications | Browser pass with an **in-memory email test double**: OTP verification, original-email status-update request and staff send; an alternate verified address remains `needs_review` and cannot receive the private status update. With SMTP absent, the UI truthfully reports that no email was sent. **Real email delivery was not verified.** |
| Inquiry acceptance/decline | Browser pass: cancel acceptance with Escape; actual acceptance creates exactly one linked Pending order without reserving stock; decline changes inquiry status without changing stock. Atomic duplicate/concurrency cases pass backend tests. |
| Official order lifecycle | Browser pass: approve, reserve, fulfill and completed tracking. Manual Pending order creation and cancellation also pass. |
| Inventory | Browser pass: receipt adds 7 units for a separate synthetic item. Lifecycle item starts with early-expiry 2 + later-expiry 3; approval reserves 3 (earliest batch first), fulfillment leaves physical stock 2 and reservations 0. Backend tests additionally cover concurrency, rollback, repeated actions, restrictions and adjustments. |
| Invoices | Browser pass: order-linked draft, explicit test price PHP25.50 × 3 = PHP76.50, issue; authenticated Superadmin API void. Draft/issue/void preserve stock. OS printing, physical printers and PDF output were not exercised. |
| Analytics | Browser/API pass: report renders and includes the fulfilled test order. Backend aggregation and RBAC checks pass. |
| RBAC | Browser pass: Sub-admin operational workflows, Admin read-only controls, direct Admin product POST rejected with 403, no Admin brochure dry-run control; Superadmin invoice void allowed. Backend authorization/session regressions pass. |
| Brochure CSV/review | Browser pass: CSV loads one incomplete draft without creating products; missing mappings fail dry run; duplicate candidate rows fail CSV loading. Reviewed single-record dry run creates no product; existing SKU supplied in different case is rejected. No approval/import button was used. |

**Browser findings and fix**

- **Fixed:** Add to My Order from the native product dialog opened the cart drawer behind that dialog. Adding now closes product details and exposes the drawer. The final browser run verifies this without an Escape workaround.
- **Remaining, cosmetic:** the desktop product dialog anchors at the upper-left instead of centering; controls remain usable. See [desktop capture](uat/desktop-product-gallery.png). Left unchanged under the feature-development pause.
- The 390 × 844 mobile product dialog fills the viewport and scrolls; mobile navigation exposes Track My Order. Stable captures: [mobile gallery](uat/mobile-product-gallery.png), [mobile navigation](uat/mobile-uat.png). Animation was disabled for screenshots to avoid mistaking a transition frame for translucent navigation.
- Final functional run: zero browser runtime errors. Browser coverage is installed Chromium/Edge at 1440 × 1000 and mobile emulation at 390 × 844; Firefox, Safari, physical touch devices and assistive-technology UAT remain unverified.

**Missing data and dependencies**

- Active local SMTP host is blank. OTP and staff-mail integration passed using memory capture, with no real mail sent. Genuine provider credentials, sender configuration and an external mailbox delivery check are still needed.
- CSV audit: exactly **124 unique rows**, exactly the 124 source-clear manifest candidates, **28 columns**, including source page/name/category, description/features/specifications, images/validation, missing fields, source/approval status and staff decisions. Zero rows selected or approved; zero genuine SKU/unit mappings entered. Models and images need explicit staff review. No manufacturer is documented by the current PDF; brand must not be treated as manufacturer evidence.
- Eleven source-conflict holds and 131 broad families/offerings remain outside the source-clear list. Three Alpha Care PNGs exceed the upload size limit. These are review/data blockers, not reasons to invent identifiers, models or imagery.
- The local MongoDB replica set was available. Batch/transaction behavior was tested using the existing isolated-fixture pattern: startup with batch mode off, then enable the actual batch services only inside the test process. This does not certify a new active-database migration or readiness marker.
- Dashboard Google Fonts and the storefront home hero's Unsplash image depend on external asset hosts; offline availability was not certified. No external payment, carrier or email-provider integration was certified by this UAT.
- Starting the updated application against iraseth_dev may create the new SKU index. That schema rollout is still separate from this UAT; the updated backend was not started against iraseth_dev.

**Checks and reproduction**

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider -k "not test_actual_124_clear_sources_approve_without_inventory_or_price_changes"
```

Result: **201 passed, 1 deselected**. The deselected test imports actual brochure candidates and was intentionally not run.

From `frontend`: `npm.cmd run build` and `npm.cmd run test:brochure` passed. From `storefront-next`: `npm.cmd run typecheck`, `npm.cmd test`, `npm.cmd run build`, and `node tests/local-uat.mjs` passed. The UAT runner requires that dashboard/storefront builds exist, installed Edge/Chrome or Playwright Chromium, and the guarded local `.env.test` settings. It starts temporary servers on 5011, 3101 and 5174 and cleans its own business fixtures. It never calls brochure approval. See [14-scenario result](uat/browser-uat-results.json).

The current untouched CSV was also run through the standalone command below. It correctly stopped with “Mark 1 to 30 rows include_in_batch=true; obtain genuine mappings and review decisions first.” This occurred **before database connection or Flask application import**, and no success report was created.

For a future genuine selected batch, the exact **read-only** procedure before any iraseth_dev modification remains:

1. Staff verify the actual SKU, selling unit, documented/verified model and explicit image decision against the source and supplier evidence. Select 1–5 genuine rows initially, at most 30. Do not substitute test identifiers or approve source holds.
2. Keep the existing environment files unchanged. Do not start/restart the updated Flask app against iraseth_dev for this step.
3. From the repository root, use a new report filename:

   ```powershell
   backend\.venv\Scripts\python.exe backend\tools\dry_run_brochure_mapping.py --mapping docs\brochure\staff-mapping-template.csv --database iraseth_dev --report docs\brochure\staff-dry-run-20261116-batch01.json
   ```

4. Review the exact database, source/catalog/selection hashes, identities, units, model/image decisions, zero quantities and null public prices. Stop. This command does not start Flask, create indexes, create approval tokens or write database records. A changed mapping/source/catalog requires a new dry run. Separate explicit authorization is still required before schema rollout or any selected-record import. Full staff steps: [development approval procedure](brochure/DEV_APPROVAL_PROCEDURE.md).

**Preservation and files changed in this UAT**

Before/after comparisons matched the complete sorted-document hashes and counts of 18 iraseth_dev business/metadata collections, including products, batches, movements, reservations, orders, inquiries, invoices and brochure imports. The products/orders/quotations/batches index definitions also matched. The active catalog remains at 3 products. The SHA-256 of `git diff --cached --binary` matched the baseline: existing staging was preserved. No commits, pushes, resets, deployments, active schema changes or environment edits were performed.

Browser fixture products, inquiries, orders, invoices, batches, reservations, stock movements, catalog events, staff users and inventory operations were verified absent after cleanup. Normal test rate-limit counters use their existing TTL expiry; browser runs receive a per-run synthetic client identity so existing counters are not reset or deleted.

Only these existing source files changed during this UAT; earlier local changes in them were retained:

- `storefront-next/components/ProductDetail.tsx`: optional callback after adding to My Order.
- `storefront-next/components/ProductModal.tsx`: close the product dialog route after a successful add.
- `backend/tools/browser_qa_server.py`: optional test-only UAT fixtures, actual batch service setup, token-protected fixture inspection, memory mail capture, isolated client-rate-limit context and scoped cleanup for linked records/support sessions. Its default legacy browser fixture behavior is retained.

New files for this task: `storefront-next/tests/local-uat.mjs`, this report, `docs/uat/browser-uat-results.json`, `docs/uat/desktop-product-gallery.png`, `docs/uat/mobile-product-gallery.png` and `docs/uat/mobile-uat.png`. All other pre-existing local files and Git staging were preserved.
