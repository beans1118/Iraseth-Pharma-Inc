Staff mapping and small-batch approval workflow

16 November 2026, Asia/Shanghai. Local branch: `feature/storefront-modernization`.

The requested template verification and staff workflow are implemented. No products, stock, pricing, environment settings or indexes were written to iraseth_dev. Its three existing products were accessed by direct read-only matching/schema checks only. No commit, push, reset or deployment was performed; existing staged/unstaged/untracked work was preserved.

1. **Verified mapping template**

   `staff-mapping-template.csv` contains exactly **124 unique source-clear candidate IDs and 28 columns**. It now includes:

   - Source PDF filename and physical page, candidate key, product name and category.
   - Documented brand/manufacturer, description, complete supported features and specifications.
   - Source-image paths, image-review status, upload validation and low-resolution flags; an empty list clearly identifies absent individual imagery.
   - Documented models, missing identity/optional fields, source status and staff approval status.
   - Explicit staff batch selection, genuine SKU and selling unit, model decision/value/evidence, image decision/approval, review notes, staff attestation and duplicate review.

   Source cells are reference material, never accepted as replacements for the live manifest. Staff-entered cells are preserved when regenerating the file. Unknown/duplicate candidate keys stop regeneration instead of dropping staff work. The download endpoint is authenticated and read-only. All current staff SKU/unit cells remain blank, decisions remain pending, and staff/image approval flags remain false. Review keys and test IDs are not proposed live SKUs.

2. **Staff-friendly approval flow**

   Download the current CSV in Brochure Review, review the source facts and fill genuine staff decisions. Start with 1-5 rows; mark only those `include_in_batch=true`, with a maximum of 30. Load the file through **Load selected batch CSV (draft only)**. The loader rejects unknown/blocked candidates, duplicate candidate IDs, duplicate comparison-equivalent selected SKUs, malformed CSV/flags and oversized batches. It cannot silently replace an existing draft. Draft loading never inserts or approves products.

   Review each selected card. The SKU/unit must come from the staff registry or supporting supplier documentation, not an inferred identifier or pack count. Model choices are explicit:

   - `use_documented`: approve the exact printed model.
   - `not_documented`: leave an absent model blank; no guessed value.
   - `staff_verified`: enter the genuine model and a supporting supplier/document reference. A value conflicting with a known printed model is blocked. Evidence is recorded for staff audit, not verified automatically by an external supplier service.

   Images require `include` or `omit`. Inclusion additionally requires visual approval and valid, correctly associated source images. Missing/oversized imagery cannot be silently substituted. Each selection/decision change invalidates the prior API dry run and final confirmation. The dry run shows the target database, exact IDs/units/models, source-backed metadata and image decisions/counts before the explicit selected-record approval step. Admin remains view-only; existing Superadmin and Sub-Admin permissions are preserved.

3. **Duplicate and ambiguity protection**

   SKUs are compared with Unicode NFKC normalization, trimming and case folding. The actual stored ID retains its entered case and identity under the existing product validation. Duplicate selected IDs and legacy catalog matches are rejected before insertion. New product creation, identifier edits and brochure imports also use a unique partial `_sku_key` index, which prevents concurrent comparison-equivalent IDs from being inserted. A concurrent two-candidate/case-variant test produced exactly one successful import and one rejection.

   No legacy IDs are rewritten or backfilled. The new index was exercised in iraseth_test only; a read-only schema check confirmed it is absent from iraseth_dev. Active rollout would be a separately authorized schema change. The existing source-identity unique index, transaction, audit events and idempotency remain in place. Source holds and broad families cannot be approved through a generic checkbox or a CSV. Possible catalog duplicates need an explicit, documented staff distinction; exact matches stay blocked.

4. **Exact dry run before any iraseth_dev modification**

   Use `DEV_APPROVAL_PROCEDURE.md`. Its first phase is now a standalone command that does **not** import/start Flask, call `ensure_indexes`, create an index, obtain an approval token or write database records. This distinction matters because starting the updated Flask application would create indexes.

   After entering actual approved staff mappings and selecting a small batch in the CSV, run from the repository root:

   ```powershell
   backend\.venv\Scripts\python.exe backend\tools\dry_run_brochure_mapping.py --mapping docs\brochure\staff-mapping-template.csv --database iraseth_dev --report docs\brochure\staff-dry-run-review.json
   ```

   The existing environment must already target iraseth_dev; it is not changed. The command reads catalog identities, applies the same selection and product validators, and writes only a new local review report if requested. Existing report files are refused to preserve prior evidence. Inspect its target/source/catalog/selection hashes, exact metadata and image choices, zero quantities and null public prices. **Stop here under the current authorization.**

   Running the command against today's untouched template correctly returns a blocked result before querying MongoDB: no batch/genuine mappings have been selected. No fake mappings were inserted to manufacture a successful active dry run. A successful validator path was separately tested against isolated fixtures while database mutation/index methods were patched to raise.

   Only after later explicit selected-record and schema-rollout authorization may the updated backend be started against iraseth_dev, followed by a fresh API dry run and the final approval. API tokens remain bound to actor, database, source, catalog and selections and expire after 15 minutes. The standalone report never authorizes an import.

5. **Checks and results**

   | Check | Result |
   |---|---|
   | Isolated database preflight | Confirmed APP_ENV=testing, iraseth_test, 127.0.0.1:27017, rs0 before write tests |
   | Existing brochure/metadata regressions after decision changes | 53 passed |
   | New staff-workflow tests | 12 passed, including CSV coverage/preservation, explicit decisions and concurrent SKU collision |
   | Full backend regression | 201 passed in 138.21 seconds |
   | Additional standalone read-only validator check | 1 passed; mutation/index methods blocked |
   | Dashboard build and `npm run test:brochure` | TypeScript/Vite build and CSV parsing/draft tests passed |
   | Next.js typecheck, npm test and production build | Passed; no competing Next.js writer during production build |
   | Browser suite | All seven groups passed, including CSV download/load, source-metadata tamper rejection, model/image review, dry run and actual Microfusion approval/public display in iraseth_test only |

   The existing actual-source integration still tests 124 source-clear records in five approved batches, with nine source images, zero stock/null public prices, idempotent retries and no changes to original products or the nine inventory/order/invoice collections fingerprinted. Browser testing verified the draft does not inherit a fabricated CSV product name or an automatic staff attestation. It found and resolved ambiguous model/image dropdown labels. Owned test servers and disposable fixtures are cleaned up after tests.

6. **Remaining blockers**

   - No genuine staff SKU/unit mappings or active-import approval exist yet. All 124 mapping rows remain pending. The generator does not invent those values.
   - The wider 266-record source still contains 11 source-conflicted records and 131 families/offerings, excluded from direct import. Their source/model/category issues need separate evidence and review.
   - Only four explicit model identifiers are documented; absent models may remain blank only after an explicit staff decision. Unknown manufacturers remain blank and separate from brands.
   - Three Alpha Care source PNGs exceed upload limits; three source images are low resolution. Image omission is supported; replacements/associations need staff approval.
   - The new SKU index is code-only for iraseth_dev. Do not start the updated active backend during the pre-modification dry-run phase. Later schema rollout and selected-record insertion require explicit authorization.

7. **Code and documentation changes in this task**

   | Change | Path |
   |---|---|
   | Modified | `backend/extensions.py` |
   | Modified | `backend/modules/product_metadata.py` |
   | Modified | `backend/routes/products.py` |
   | Modified | `backend/modules/brochure/routes.py` |
   | Modified | `backend/modules/public_catalog/routes.py` |
   | Modified | `backend/tools/prepare_brochure_review.py` |
   | Modified | `backend/tests/test_brochure_import.py` |
   | Modified | `backend/tests/test_brochure_real_manifest.py` |
   | Modified | `backend/tests/test_product_metadata.py` |
   | Modified | `frontend/package.json` |
   | Modified | `frontend/src/BrochureReview.tsx` |
   | Modified | `storefront-next/lib/catalog.ts` |
   | Modified | `storefront-next/components/ProductDetail.tsx` |
   | Modified | `storefront-next/tests/browser-e2e.mjs` |
   | Modified | `docs/brochure/staff-mapping-template.csv` |
   | Modified | `docs/brochure/reviewed-candidates.json` |
   | Modified | `docs/brochure/DEV_APPROVAL_PROCEDURE.md` |
   | Created | `backend/modules/brochure/review_sheet.py` |
   | Created | `backend/tools/dry_run_brochure_mapping.py` |
   | Created | `backend/tests/test_brochure_staff_workflow.py` |
   | Created | `frontend/src/brochure-mapping.ts` |
   | Created | `frontend/tests/brochure-mapping.mjs` |
   | Created | `docs/brochure/STAFF_APPROVAL_WORKFLOW_REPORT.md` |
