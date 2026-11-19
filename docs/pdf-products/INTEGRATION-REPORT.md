# Existing product-system PDF integration

2026-11-16 · `feature/storefront-modernization`

Implemented and verified in `iraseth_test`. **No products were added to `iraseth_dev`.** Its original three products, checked stock/order/invoice data, four checked index sets and Git staging remained unchanged. No source files were deleted; no commit, push, merge or deployment was performed.

## Result

The PDF preparation now creates ordinary records through the existing product validator and persistence service into the existing `products` collection. The existing Flask public API and Next.js Products page display these records dynamically. The existing employee product editor handles metadata and explicit genuine SKU/unit confirmation; the existing batch inventory service handles subsequent real receipts. There is no additional public catalog, product collection, model class, API route or management screen.

The schema requires product ID and unit, so a marked temporary internal ID and pending-unit marker are used until staff confirmation. The ID is stable for product URLs and stock/order references. Genuine `sku` is stored separately after confirmation. Legacy/manual products retain their existing ID-as-SKU behavior without a data backfill. Unknown internal prices remain null, including future unpriced order amounts and email/dashboard presentation; invoice prices remain explicit.

## Ready products and remaining blockers

| Group | Count | Result |
| --- | ---: | --- |
| Individually described, source-clear candidates | 124 | Eligible for selected provisional creation, subject to duplicate review and later development-write authorization |
| First selected batch passing the actual read-only development dry run | 5 | Microfusion Set, Polyvol, Photofusion Set, Blood Administration Set, Haemofusor Set |
| Individually described candidates with source conflicts | 11 | Blocked; clarify source/model/variant/name/category before selection |
| Families or offerings | 131 | Excluded; identify actual sellable products before creating records |
| Genuine staff SKU/unit mappings available | 0 | Receiving and SKU-dependent operations remain blocked for all provisional products |
| Documented manufacturer | 0 | Empty; do not infer from brand/logo |
| Candidates with documented model identifiers | 4 | Preserve source identifiers; other models stay empty unless verified later |
| Candidates with included, individually matched source images | 8 | Existing image upload validation applies |

The remaining 116 source-clear records use placeholders until appropriate imagery is available. Two Alpha Care records have oversized source images; Oncofusion's multiple-configuration image is deliberately omitted. Related source names need documented per-candidate duplicate resolution, including matches within a proposed batch; source clarity alone does not authorize importing every variant together. Exact existing names/source identities/identifiers cannot be imported twice.

The [124-row source-clear list](source-clear-products.csv) has unique candidate keys and matches the complete candidate set in the existing staff mapping template. It lists source pages, names, categories, descriptions, features, specifications, documented brands/models, image choices, missing fields, related source candidates and pending approval status. The original manifest, staff template and review files were preserved.

The source is the user-approved local `Core Product A5 (2).pdf` copy. The [image review](../brochure/pdf-product-image-review.json) documents technical panel comparisons; it is not a claim of genuine SKU/unit, supplier or clinical approval.

## Safety and staff behavior

- Imports start with quantity/baseline zero, internal/public price null and no batches, receipts, movements, reservations, orders or invoices. Public output shows Out of Stock and Price Upon Request; Add to My Order is disabled.
- Server-side identity gates protect receiving, release/allocation, adjustments, inquiry acceptance, legacy fulfillment, manual orders and invoices. Public numeric price approval is blocked while identity is pending. Changing unit text alone cannot unlock stock operations.
- The existing **Edit metadata** form identifies the temporary ID, preserves gallery/content, permits documented model editing, and requires an explicit checkbox plus evidence before genuine SKU/unit confirmation. Confirmation is transactional and audited. Normal metadata edits preserve identity, quantities and relationships.
- Normalized comparison keys, existing-ID/SKU checks, unique indexes and transactional rechecks protect duplicate creation/confirmation, including concurrent confirmation of the same SKU. Exact PDF source/candidate identity is unique. Repeating an already-completed source selection skips it without replacing staff edits.
- One-time preparation is read-only by default, limited to 1–30 explicitly selected candidates and local test/development targets. Apply requires the exact reviewed report, confirmed target and an existing active authorized staff actor. Source/content/catalog changes invalidate a pending plan. No automatic ambiguous import is permitted.

## Verification

| Check | Result |
| --- | --- |
| Backend regression suite in `iraseth_test` | **224 passed, 1 deselected**, 144.82 seconds |
| New actual-PDF integration tests | All 9 passed within that suite |
| Dashboard TypeScript + Vite production build | Passed; both test API build and normal local build verified |
| Dashboard CSV and deployment guard tests | Passed; 124 template rows, duplicate/draft/source checks and environment guards |
| Next.js TypeScript, source/syntax/API/gallery/image/tracking/deployment/inquiry tests | Passed |
| Next.js production build | Passed with existing Next 15.5.29 and native Sharp image pipeline |
| Headless browser UAT | **16 passed**, no browser runtime errors or reported UI issues |
| Actual development-database selected dry run | Passed for 5 products, no application startup, record writes or index creation |
| Original staff mapping template vs new source-clear list | Exactly the same 124 unique candidate keys |
| Disposable test cleanup | No actual PDF fixture products, browser products or browser staff remaining |
| Git whitespace check | Passed; existing Windows line-ending notices only |

Backend command from `backend/`:

```powershell
.venv\Scripts\python.exe -m pytest tests -q -k "not test_actual_124_clear_sources_approve_without_inventory_or_price_changes" -p no:cacheprovider
```

The deselected older test bulk-simulates approved genuine SKU/unit mappings for all 124 sources. Its previous verification is retained in the earlier reports; current actual-PDF coverage instead tests the requested provisional identity behavior, in batches, without suggesting a genuine mapping. The new coverage includes all 124 actual products/public DTOs, repeat runs, zero stock/null prices, SKU races, source holds, same-batch possible duplicates, metadata/identity confirmation, receipt after confirmation, and unpriced inquiry → order → reservation → fulfillment → explicitly priced invoice.

Browser coverage includes an actual Microfusion source image/content on the existing Next modal and stable product URL, staff editing/identity gating/receipt, gallery uploads and carousel, >100-record pagination, search/category/brand/stock filters, My Order, reference-only tracking, verified communications, inquiry accept/decline, official order approval/FEFO fulfillment, invoices, analytics, Admin RBAC, mobile layout and CSV dry-run/duplicate checks. All QA identifiers, unit mappings, receipts and invoice prices are clearly isolated test simulations, not proposed live values.

The first browser attempt correctly prevented selecting Microfusion again in the old review scenario after the new PDF fixture had already created it. The fixture selector was corrected to use an unimported candidate; the following full 16-scenario run passed. A subsequent model-field check also needed its selector to allow the label help text. These initial failure artifacts are retained in `verification/`; they document test-fixture selector mismatches, not duplicate-import bypasses. Final verification is in [the browser results](verification/final-complete/browser-uat-results.json). SMTP was simulated in memory; external email delivery and cloud hosting/Atlas were not exercised by this local task.

## Exact files changed for this task

Existing files changed relative to the start of this task (including files that were already untracked before the task):

| Path | Change |
| --- | --- |
| `backend/modules/product_metadata.py` | Shared identity state, normalized ID/SKU comparison and marked temporary identity constants |
| `backend/routes/products.py` | Provisional creation through existing validation, null price handling, genuine identity confirmation and duplicate protection |
| `backend/modules/inventory/service.py` | Identity gate for batch receiving/allocation/adjustment operations |
| `backend/routes/inventory.py` | Identity gate in legacy stock operations |
| `backend/routes/orders.py` | Pending-identity guards and honest unknown order pricing |
| `backend/modules/quotations/routes.py` | Pending-identity guards and nullable accepted-order pricing |
| `backend/modules/invoices/routes.py` | Pending-identity guard before invoice creation |
| `backend/modules/public_catalog/routes.py` | Pending products always unavailable/unpriced; existing public DTO/route retained |
| `backend/utils/email.py` | Price Upon Request for orders with unknown totals |
| `backend/modules/brochure/service.py` | Guarded provisional selections using existing source assessment and image decisions |
| `backend/modules/brochure/routes.py` | Reuse existing preparation/persistence, check ID and SKU, check duplicates within the selected batch |
| `frontend/src/api.ts` | Existing product/order types support model, genuine SKU, identity state and null amounts |
| `frontend/src/ProductEditor.tsx` | Same editor exposes genuine confirmation/evidence and documented model field |
| `frontend/src/App.tsx` | Clear provisional labels/search, block pending operation choices and show unknown amounts honestly |
| `frontend/src/Invoices.tsx` | Pending products disabled in invoice selection |
| `backend/tools/browser_qa_server.py` | Optional actual-PDF fixture and cleanup confined to `iraseth_test` |
| `storefront-next/tests/local-uat.mjs` | Actual-PDF existing-page/editor coverage and separate test artifact destinations |
| `docs/brochure/DEV_APPROVAL_PROCEDURE.md` | Link to the corrected provisional-product procedure; older genuine-SKU option retained |

New code files: `backend/tools/add_pdf_products.py`, `backend/tests/test_pdf_products_existing_system.py`.

New preparation/evidence files: `docs/brochure/pdf-product-image-review.json`; this `docs/pdf-products/` directory contains the procedure, 124-row list, selected dry-run report, this integration report and verification JSON/screenshots. None is an additional customer catalog or product management screen. No dependencies, secrets, environment files, stock seed files or existing storefront components were changed in this task. Existing Git staging and unrelated local work were preserved.

## Next operation

Review [the exact selected-batch procedure](EXISTING-PRODUCTS-PROCEDURE.md) and [five-product dry-run report](dev-first-batch-dry-run.json). A later explicit authorization is required before any `iraseth_dev` product/index write. Genuine SKU/unit records are required before receiving stock; missing models/manufacturers/images require evidence rather than invented values. There is no need to add another catalog or management workflow.

Use the updated backend/dashboard before reopening staff access after a later authorized apply; an older running process does not acquire these guards automatically. Development application startup/index changes were deliberately not performed in this task.

[Data-safety evidence](verification/data-safety.json) records equal before/after counts and document hashes for 18 development collections, unchanged index sets and unchanged staged-diff hash.

[Exact path audit](verification/files-changed.json) lists every modified/new path relative to this task's baseline, including retained browser artifacts. The final check again confirmed 16 browser passes, zero remaining PDF/browser product fixtures, unchanged development data/indexes and unchanged Git staging.
