Core products integration review and isolated import verification

16 November 2026, Asia/Shanghai. Branch: `feature/storefront-modernization`.

The authorized test-only integration is complete. `iraseth_dev` was used only for direct, read-only identity matching; it was not imported into or modified. The user confirmed that no actual SKU/selling-unit mapping is available and requested the reviewed list and test-only import. No staff identity, manufacturer, SKU, unit, model, image approval or price was invented for active use. The original PDF and 266-record source manifest remain unchanged.

1. **Review results**

   | Classification | Records | Next step |
   |---|---:|---|
   | Source clear | 124 | Obtain actual SKU/unit mapping and explicit selected-record staff approval |
   | Source clarification required | 11 | Corroborate identity/category/gauge; generic approval checkbox cannot bypass the hold |
   | Family or offering | 131 | Identify an individual product/model first |
   | Fully ready for iraseth_dev insertion | 0 | All 266 lack staff-approved SKU and selling unit |

   Read-only matching against the three existing `iraseth_dev` product records found 266 New source matches, zero Existing and zero Ambiguous existing-catalog matches. This does not mean all 266 are individual products or approved insertions. Source-family/variant relationships remain separate from catalog duplicate matches.

   The earlier repeated High Quality Ductless Fume Hood listing is already merged, preserving two source occurrences. No duplicate normalized names remain in the manifest. Four overlapping radiography family names remain flagged for staff review rather than being assigned invented models. Clinical test concentration, cassette/strip, specimen and drug-panel variants remain individually distinct.

   All 266 lack a documented manufacturer; a documented brand is not substituted as manufacturer. Only four ENT entries have explicit model identifiers: VL3D, VL3R, VLDM and VLRM. The other 262 do not document a separate model code. Source descriptions/features are absent for 207 records and specifications for 210; missing optional content remains empty. A category name or product listing is not converted into invented medical specifications.

   The complete per-record review is in `SOURCE_REVIEW.md` and `reviewed-candidates.json`. `staff-mapping-template.csv` contains the 124 source-clear candidates with blank staff SKU/unit/review values. Those source-clear records are ready for identity review, not insertion without it.

2. **Unresolved source and image items**

   - Glucoseth: conflicting battery statements and an unrelated centrifuge paragraph; verify the exact meter source/model. The unrelated paragraph and conflicting power values remain excluded from proposed public metadata.
   - Polyflex / Polyflon PUR options: exact gauge availability is not documented; no material/gauge cross-product is inferred.
   - Four printed names/variants require clarification: Chlamydia Trachomatics, Chikugunya, Hepatits A and Bacterial Vaginosis (Variety). No silent clinical-name correction is applied.
   - Four HIV/Syphilis cassette/strip entries need customer-facing category confirmation because the brochure places them under Hepatitis Markers. Original provenance is preserved.
   - Broad families include the Polywin Safety/Polycan Safety without-port versus generic port-feature contradictions and the ambiguous Table Type Steam Sterilizer Infant Incubator listing. These records cannot be directly imported as an identified individual product. The unclear Polyflon LATER FREE claim remains omitted; it is not turned into a latex-free claim.
   - Twenty source images were inspected technically: 17 pass the existing image controls, three Alpha Care PNGs exceed 200,000 bytes, and three images are low resolution. The tests included nine valid images belonging to source-clear records. Passing technical validation is not active staff image approval. Generic collages and family illustrations are not assigned to undocumented variants.

3. **Implementation changes**

   - Added source-readiness assessment that distinguishes a clear source identity from missing SKU/unit, staff approval, optional content and model evidence. The staff preview now presents those distinctions and can filter them. Unresolved source holds are blocked by the server as well as the selection UI.
   - Separated `brand` from `manufacturer` in product validation, employee editing, brochure preparation and the public catalog. Imported brands remain available to storefront brand filters; absent manufacturers stay empty. Legacy combined values retain their brand fallback without being newly declared documented manufacturers.
   - Added a visible database target to the staff preview/dry run and bound signed approval tokens to that database, in addition to actor/source/selection/catalog. A token for a different target is rejected.
   - Extended tests to use actual manifest candidates, supported descriptions/features/specifications and real source images through staff-authenticated dry-run/approval endpoints. The storefront remains dynamic: no brochure array was added to the public Products page.

4. **Tests and verification**

   | Check | Result |
   |---|---|
   | Isolated target preflight | Confirmed `.env.test` APP_ENV=testing, database iraseth_test, 127.0.0.1:27017, replica set rs0 before writing tests |
   | Targeted integration/metadata/public catalog run | 58 passed before the final brand/target checks were added |
   | Full backend regression | 188 passed in 130.48 seconds |
   | Final model-evidence/source assessment check | 1 passed after the final optional model-readiness annotation |
   | Dashboard production build | TypeScript and Vite build passed |
   | Next.js typecheck and production build | Passed; no other Next.js writer was running during the build |
   | Storefront npm test | Smoke, UI regression, syntax, catalog failures/pagination, gallery controls, tracking proxy and inquiry retry checks passed |
   | Browser suite | All seven check groups passed, including actual brochure approval to public storefront in iraseth_test |
   | Git whitespace check | Passed; existing line-ending notices only |

   The real-manifest backend test imported all 124 source-clear records in five batches (maximum 30 per batch), with nine source images and 124 catalog audit events. It used clearly marked disposable `PYTEST-BROCHURE-...` identifiers and `QA_TEST_UNIT`; these are test fixtures and are never proposed active SKUs/units. Every import went through the existing shared product validator and insertion path, authenticated approval, a fresh signed dry run and MongoDB transactions.

   Every approved batch was retried with the same operation key: no duplicate products appeared. Existing source identities are then classified Existing and cannot be inserted again under a new operation. All imported records had zero stock/baseline and no approved public price; descriptions, features and specifications matched the source exactly and unknown manufacturers remained blank. Every imported item was returned by the real public API, including records after page 1.

   Fingerprints of original test products and nine inventory/order/invoice collections were unchanged by brochure import: inventory_batches, inventory_logs, stock_movements, stock_reservations, inventory_operations, inventory_adjustments, orders, invoices and invoice_events. No brochure import created a stock batch, receipt, reservation, order or invoice. All eleven source-conflicted candidates were tested for rejection despite generic review/duplicate flags. Existing RBAC, inventory, inquiry, fulfillment and invoice regression tests remain green.

   The browser test used an ephemeral, authenticated Sub-Admin session on a server hard-locked to iraseth_test. It selected Microfusion Set, reviewed its actual image, supplied disposable test identity/unit, ran a dry run and explicitly approved it. The Next.js Products page then displayed the real API record. Its modal showed the source image, features/specifications and POLYMED brand, no invented manufacturer, Price Upon Request and Out of Stock; Add to My Order was disabled. The real POLYMED filter retained the record. Existing >100-product pagination, multi-image gallery, keyboard focus, URL history, mobile layout and Admin view-only checks also passed.

   Cleanup verification found zero remaining `PYTEST-BROCHURE-` and `PYTEST-BROWSER-` products, catalog audit events or import operations. Owned test servers were stopped. Test imports therefore do not make brochure products appear in the active storefront.

5. **Exact iraseth_dev approval procedure**

   Follow `DEV_APPROVAL_PROCEDURE.md`. In brief: obtain actual SKU/unit mappings and owner authorization for named records; sign in with an existing authorized role; verify Catalog database: iraseth_dev; select only source-clear, distinct records; review optional images; run a dry run for at most 30 records; verify the displayed target and metadata; then explicitly approve only the authorized batch with the same selections and durable idempotency key. Never use the test identities or auto-import all 266. Source/catalog/selection changes or token expiry require another dry run.

   After approval, the existing Flask public catalog/Next.js pipeline publishes the selected metadata using current visibility rules. Stock remains zero and public price remains null until separate authorized receiving/pricing workflows occur. No active-database step from that procedure was executed in this task. Real SKU/unit mappings, source resolutions and explicit selected-record authorization remain the prerequisites for active integration.

6. **Exact files changed in this task**

   Earlier staged, unstaged and untracked work was inspected and preserved; the Git index was not changed. The following list excludes pre-existing edits from the earlier development task, ignored build/cache files and disposable test-database fixtures. No dependency install/upgrade, commit, push, reset or deployment was performed in this task.

   | Change | Path |
   |---|---|
   | Modified | `backend/modules/brochure/service.py` |
   | Modified | `backend/modules/brochure/routes.py` |
   | Modified | `backend/modules/product_metadata.py` |
   | Modified | `backend/routes/products.py` |
   | Modified | `backend/modules/public_catalog/routes.py` |
   | Modified | `backend/tools/preview_brochure.py` |
   | Modified | `backend/tools/browser_qa_server.py` |
   | Modified | `backend/tests/test_brochure_import.py` |
   | Modified | `backend/tests/test_product_metadata.py` |
   | Modified | `frontend/src/api.ts` |
   | Modified | `frontend/src/ProductEditor.tsx` |
   | Modified | `frontend/src/BrochureReview.tsx` |
   | Modified | `storefront-next/lib/catalog.ts` |
   | Modified | `storefront-next/components/ProductDetail.tsx` |
   | Modified | `storefront-next/tests/browser-e2e.mjs` |
   | Created | `backend/modules/brochure/assessment.py` |
   | Created | `backend/tools/prepare_brochure_review.py` |
   | Created | `backend/tests/test_brochure_real_manifest.py` |
   | Created | `docs/brochure/reviewed-candidates.json` |
   | Created | `docs/brochure/staff-mapping-template.csv` |
   | Created | `docs/brochure/SOURCE_REVIEW.md` |
   | Created | `docs/brochure/DEV_APPROVAL_PROCEDURE.md` |
   | Created | `docs/brochure/CORE_PRODUCTS_INTEGRATION_REPORT.md` |
