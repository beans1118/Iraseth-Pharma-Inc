# PDF product image completion report

Current branch: `feature/storefront-modernization`. Local target: **`iraseth_dev` at `127.0.0.1:27017`**. Production was not accessed.

## Recovery and source review

The interrupted work had started the audit but had made **no development image updates**. The earlier Alpha Care WebPs were already prepared and tested. They were reused without rewriting the source PNGs or repeating the preceding product-management redesign.

The complete 124-product source-clear set and all 127 current product records were rechecked against the user-approved local `Core Product A5 (2).pdf` copy, SHA-256 `4d1ac212740e739c6b5853231270cce2af22e66529916abc6835910b976a7696`. This is the previously accepted copy of the PDF referred to as `(2)(1)` in the request.

The source page review includes the individual product panels, sizing tables, page-12 rapid-test assortment and pages 13–15. Pages 13–15 do not contain individually usable photographs for the four imported ENT models. Family syringe/cannula pictures do not identify an exact needle/gauge/capacity combination. Cropping those pictures would not establish the missing identity.

At native resolution, the page-12 assortment photo contains a box explicitly labelled **Dengue IgG/IgM**. A lossless crop isolates that box. The neighbouring **HBsAg** label says only “One Step Rapid Test Device” and does not establish cassette versus strip; its review crop remains unapproved and was not applied. The occluded FOB box and excluded HIV/Syphilis entries were not used for other products.

## Outcome for all 124 PDF products

| Audit category | Products | Action |
| --- | ---: | --- |
| Verified new image mapping | **3** | Updated existing image/gallery fields; four image files total |
| Correct existing galleries | **8** | Preserved bytes and order |
| Ambiguous source imagery | **39** | Kept neutral placeholders; reasons recorded per product |
| No individually usable source image | **74** | Kept neutral placeholders; no substitute image invented |
| Failed image updates | **0** | No unresolved write or verification failure |

**11 of the 124 PDF products now have verified product imagery; 113 retain placeholders.** Completing the remaining placeholders requires additional product-specific images or identification evidence, not repeating generic family pictures. No new product records were created, and the full catalog remains **127 products**.

[The complete audit and validated plan](image-audit-and-plan.json) lists all 124 product identifiers, their source pages, classifications and reasons. [The operation result](image-update-results.json) records the exact updated identifiers, image files, audit-event IDs and browser results.

## Exact verified updates

| Existing product / stable internal ID | Gallery in order | Source / validation |
| --- | --- | --- |
| Alpha Care Adult Diaper - XL — `TMP-PDF-4D1AC21274-P03-0DAD68E8ADCD` | [Primary image](../product-ui-cleanup/image-candidates/alpha-care-adult-diaper.webp) | PDF page 3, XL packaging; 562 × 465; lossless WebP; **169,442 bytes** |
| Alpha Care Underpads - 60 cm x 90 cm — `TMP-PDF-4D1AC21274-P03-2D486F10F85E` | [Front, primary](../product-ui-cleanup/image-candidates/alpha-care-underpads-front.webp); [side, additional](../product-ui-cleanup/image-candidates/alpha-care-underpads-side.webp) | PDF page 3, dimensions printed on packaging; both 588 × 784; WebP quality 95; **69,768 / 62,162 bytes** |
| Rapiquick Dengue IgG/IgM Rapid Test Kit — `TMP-PDF-4D1AC21274-P12-D9C681D70A9A` | [Primary source crop](candidates/rapiquick-dengue-igg-igm.webp) | PDF page 12, embedded image object 1870 at 1017 × 574; crop left 230, top 24, width 294, height 176; lossless WebP; **47,508 bytes** |

All output files are static, decodable WebP images below the actual **200,000-byte / 16-megapixel** limits. Alpha Care dimensions/aspect ratios were preserved. The Dengue crop preserves the native source pixels and label, without reconstructing text or stretching the box. Source package text was not promoted into new product descriptions or medical claims.

The [HBsAg crop](candidates/rapiquick-hbsag-label-review.webp) is retained solely as review evidence. It is not a live gallery image for either HBsAg record.

## Existing product service and data safety

The update uses the existing `routes/products.py` product service and shared `product_metadata.metadata` image validation. No collection, route, customer catalog or employee screen was added. An image-only helper is shared with the existing authenticated `PUT /api/products/<id>` route when that request contains only `image`/`images`.

The helper checks an existing active authorized editor, validates the gallery, compares its reviewed state, and changes **only `image` and `images`**. Image updates and `catalog_events` audit entries commit together. Matching retries perform no product or audit writes; a changed gallery requires fresh review. Existing additional images are retained for legacy primary-image requests. The three source updates committed together in one transaction, and their three audit events hold the source PDF hash, source/crop evidence, asset hashes and owner-authorization context.

Verified preservation:

- All 127 product documents are identical outside `image`/`images`, including IDs, genuine/provisional SKU/unit state, descriptions, categories, features, specifications, manufacturers, prices and quantities.
- The other 124 complete product records, including every original product and existing correct gallery, are unchanged.
- Inventory, batches, reservations, movements, orders, invoices, users and other protected development collections are unchanged.
- Existing audit records and all index definitions are unchanged; exactly **three image-update audit entries** were appended.
- Provisional identity restrictions remain active. Updated products remain **Out of Stock / Price Upon Request**, with Add to My Order disabled.
- Historical `brochure_source.image_review` fields describe the original import decision and were deliberately preserved. Current source-image authorization is recorded in the new image audit events. No non-image product field was rewritten to change historical review metadata.
- Existing Git staging and unrelated local work are preserved. No backup, reset, stash, source deletion, folder cleanup, commit, push, merge or deployment was performed.

## Tests and live verification

Changed application file: `backend/routes/products.py`. Added regression file: `backend/tests/test_pdf_image_updates.py`. The remaining additions are this image audit/report, two source-review crops, result/evidence files and verification artifacts. [Exact paths and preservation checks](verification/change-audit.json) list every addition/change relative to the recovery baseline. No existing files were deleted; environment files and Git staging are unchanged.

- **232 backend tests passed, 1 deselected**, using isolated `iraseth_test`. The older bulk genuine-SKU simulation remains deselected as in prior verification; current provisional integration coverage is retained.
- Six added cases cover the three actual source galleries, preservation of every non-image field, authorization/field restrictions, stale-gallery rejection, idempotent retries/audits, legacy additional-image preservation, and full transaction rollback after a later invalid image.
- Dashboard TypeScript/Vite build passed. Next.js TypeScript, source/syntax, catalog error/pagination, gallery, native Sharp, tracking/deployment and inquiry retry checks passed; production build passed.
- Read-only live API verification returned **100 + 27 unique products**. The Next.js Products page displayed the same 127 IDs across **24/24/24/24/24/7** cards per page.
- Verified all three updated cards, modal galleries and standalone URLs. Checked actual image bytes against the approved assets, primary ordering, underpad gallery arrows/keyboard/thumbnails, loaded image dimensions, Out of Stock / Price Upon Request and disabled ordering. Existing eight source galleries still match their original source-image bytes. No browser runtime errors occurred.
- Verified employee thumbnails, details galleries and editor previews for all three updated products using the actual Vite components and read-only live public product data. Authenticated network requests were intercepted; this check created no login session or database writes. The second underpad image and gallery ordering passed. An initial browser harness import used the wrong Vite CommonJS export shape; correcting that harness import produced a clean pass without changing application code.
- The existing Flask public API and Next.js live adapters publish these MongoDB image fields dynamically; no product list or image mapping was hardcoded into the storefront. The generated `.next/images-manifest.json` is not the product image database.

The local storefront preview is available at [Products](http://127.0.0.1:3000/products).

## Exact code changes

- `backend/routes/products.py`: added the narrow audited image-only helper and wired pure image requests through it; retained existing metadata editing and gallery validation.
- `backend/tests/test_pdf_image_updates.py`: added the six isolated source-image/audit/concurrency-state/rollback cases.

New source-review artifacts are limited to this `docs/product-images/` directory: the two original-source crops, the complete audit/plan, operation results, this report and verification evidence. Existing Alpha Care candidates and original PDF/PNG files were reused unchanged. See the final path/data-safety audit for the complete artifact list.

## Next cleanup phase — recommendations only

Nothing has been cleaned or deleted. Current dependency evidence suggests reviewing:

- `frontend/src/BrochureReview.tsx` and `frontend/src/brochure-review.css`: no longer mounted in the employee UI. The component still imports `brochure-mapping.ts`, which is exercised by frontend tests; do not remove that dependency blindly.
- `legacy-storefront/index.html`, `legacy-storefront/main.js`, `legacy-storefront/README.txt`: older audit identified no active build references. The entire folder is **not** automatically safe because `legacy-storefront/data.js` relates to the missing legacy `js/data.js`/`fmtPHP` chain.
- `storefront/`, generated `site/`, root `admin.html`, `js/`, `css/` and copied assets: review/retire the legacy pipeline and any external host dependencies together. `storefront/scripts/copy-admin.mjs` still copies these into `site/`, and its Vite build can overwrite that directory.

Keep `backend/`, `frontend/`, `storefront-next/`, source PDFs/images, required audit/import tooling and current dependencies. Use [the existing cleanup dependency audit](../LEGACY-CLEANUP-AUDIT.md) in a separate authorized cleanup task; do not delete folders based on this brief list.
