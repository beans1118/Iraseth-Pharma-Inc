# Product management and storefront cleanup

Branch: `feature/storefront-modernization`. The active development catalog remains **127 products: 3 original and 124 PDF products**. No development product, image, stock, price, order, invoice or audit record was changed by this task. Image changes remain pending the owner's explicit authorization.

## Employee product management

- Removed Brochure Review from the active navigation, page type, component imports and rendered dashboard. Its source files, processing modules, private API safeguards, source documents and audit history remain intact. Imported products remain ordinary All Products records.
- Replaced the unbounded product table with a searchable table that renders 25 rows by default, with a 50-row option and pagination. Product names and optional thumbnails are primary; category, available stock, batch on hand and View/Edit actions remain readable. Long IDs and identity warnings are confined to details/editing.
- View opens product metadata, gallery, full internal ID, genuine SKU/unit state, inventory summary and loaded batch information. On hand, reserved and eligible available stock remain distinct. Products omitted from a successfully loaded, non-truncated summary have no batches and show zero; missing/failed/truncated summary data is explicitly unknown. The existing summary API's 500-product cap is respected, not treated as proof of zero for omitted rows.
- Narrow screens use stacked product rows with visible actions. Details dialogs fit the viewport. Desktop retains a conventional table.
- Superadmin publication controls moved from 127 always-mounted forms beneath the table into the selected product's View interface. Their existing API and permissions remain unchanged. Admin has View only; Superadmin and authorized Sub-admin retain Edit.
- `ProductEditor.tsx` remains the single creation/edit form. Browser tests exercise persisted name/category/brand/manufacturer, description, features, specifications, model and gallery data. Primary-image reordering and additional images are preserved. Populated feature/specification textarea labels now have stable accessible names. Genuine SKU/unit confirmation restrictions remain active.

## Public categories and dynamic catalog audit

The Products page has one **Category** dropdown, defaulting to **All Categories**. Its options come from the categories in the complete API catalog. Search, brand, availability, sorting, pagination, modal galleries and standalone URLs remain in the existing components. No category names or PDF product arrays were added to the live storefront.

The active source chain is:

1. All Products → `ProductEditor` sends authenticated `POST /api/products` or `PUT /api/products/<id>` requests. Existing Flask validation/RBAC persists metadata in MongoDB `products`; stock uses the separate existing batch inventory services.
2. Flask `GET /api/public/products` and `GET /api/public/products/<id>` read that same collection. They publish visible products, sanitize metadata/gallery fields, calculate eligible batch availability, suppress pending-identity availability, and expose only approved public prices. No stock, cost or private review details are exposed.
3. Next.js `lib/catalog.ts` fetches the public API with `cache: 'no-store'`. `app/products/page.tsx` passes the complete paginated API result into `CatalogClient`, which derives filter options and paginates the visible cards.
4. The ordinary `[slug]` route and intercepted modal route call `getPublicProduct`. `ProductDetail`, `ProductModal` and `ProductGallery` render that API product. A metadata/gallery edit appears on subsequent storefront requests without rebuilding a product list.

Inspected the active Products routes, intercepted modal route, `CatalogClient.tsx`, `ProductDetail.tsx`, `ProductModal.tsx`, `ProductGallery.tsx`, `lib/catalog.ts` and Flask public catalog routes. None imports brochure manifests/review JSON as a live catalog. Static marketing content and test fixtures are separate from this data path.

## Exact image mapping proposed for authorization

The original PDF page 3, extracted PNGs and compressed candidates were visually compared. Packaging identifies the diaper as XL and the underpads as 60 cm × 90 cm. Original dimensions/aspect ratios were retained; no crop, resize, invented image or unrelated substitute was used. All three candidates pass existing static WebP, 200,000-byte and 16-megapixel upload validation.

| Existing product / internal ID | Proposed gallery, in order | Candidate size / dimensions |
| --- | --- | --- |
| Alpha Care Adult Diaper - XL — `TMP-PDF-4D1AC21274-P03-0DAD68E8ADCD` | Primary: [adult diaper](image-candidates/alpha-care-adult-diaper.webp) | 169,442 bytes; 562 × 465; lossless WebP |
| Alpha Care Underpads - 60 cm x 90 cm — `TMP-PDF-4D1AC21274-P03-2D486F10F85E` | Primary: [front](image-candidates/alpha-care-underpads-front.webp); additional: [side](image-candidates/alpha-care-underpads-side.webp) | 69,768 and 62,162 bytes; both 588 × 784; WebP quality 95 |

[The mapping proposal](image-mapping-proposal.json) records source/candidate hashes, dimensions, encodings, product IDs, ordering and pending authorization. The existing original PNGs and eight correctly associated catalog images remain unchanged. The proposal does not authorize a database write or new medical claims; original packaging text is retained as source imagery.

Oncofusion's multiple configurations, family-level syringe/cannula images, and Polyspike closure pictures do not establish the precise individual stock variants. Their placeholders remain, with reasons in the proposal's review notes. Glucoseth remains excluded because its source conflict is unresolved. No imagery was fabricated for products lacking individually identified source pictures.

## Verification

- Backend: **226 passed, 1 deselected**, in `iraseth_test` only (154.75 seconds). The deselected older all-source genuine-SKU simulation is covered by the existing provisional integration tests. The two added tests validate actual compressed Alpha Care files and image-only edits, Admin denial, unchanged metadata/stock and pending identity restrictions.
- Dashboard: TypeScript/Vite production build passed; retained private CSV-preparation and deployment guard tests passed. The test API build is restored to normal local settings after browser verification.
- Next.js: TypeScript, source/syntax, catalog pagination/errors, gallery, native image pipeline, tracking proxy, deployment and inquiry retry tests passed. Production build passed.
- Browser: **17 end-to-end scenarios passed** in isolated `iraseth_test`, including employee pagination over 100 records, compact rows/details, metadata persistence and public refresh, actual Alpha Care uploads, category dropdown, galleries, My Order, tracking, verified communications, inquiry acceptance/decline, physical/reserved/available stock (5/3/2), fulfillment, invoices, analytics and RBAC. [Browser evidence](verification/final-complete/browser-uat-results.json).
- Additional mobile checks cover the employee table, details dialog, Admin view-only controls and API-derived live category options. Development verification uses GET requests only; the live catalog still contains 127 products. Screenshots and test results are retained under `verification/`.

Screenshots show isolated QA fixtures; their product totals are test data, not the development catalog's 127 records.

The first browser startup encountered concurrent repository-owned Next dev and preview processes sharing `.next`, producing a webpack module error. Those processes were stopped for the production rebuild; one current local preview was restored. An expanded edit test exposed the populated textarea-label issue, which was fixed. The mobile test navigation helper was also corrected to open the off-screen sidebar explicitly. Earlier failed-attempt artifacts are retained separately from successful results. No remaining application failure was observed. Test communications used the existing in-memory mailer; no external email delivery was exercised.

## Exact code changes

Existing files changed:

| File | Change |
| --- | --- |
| `frontend/src/App.tsx` | Remove active brochure screen; mount paginated catalog; move publication controls into details; track successful stock-summary loading |
| `frontend/src/ProductEditor.tsx` | Stable accessible names for populated feature/specification textareas |
| `storefront-next/components/CatalogClient.tsx` | Dynamic category dropdown and correctly labelled brand filter |
| `storefront-next/app/globals.css` | Responsive filter grid for the additional category select |
| `backend/tools/browser_qa_server.py` | Optional actual Alpha Care fixtures and QA metadata projection, confined to test database |
| `storefront-next/tests/local-uat.mjs` | Verify the new dashboard, dropdown, real image candidates and retained operational flows |

New code: `frontend/src/ProductCatalog.tsx`, `frontend/src/product-catalog.css`, `backend/tests/test_cleanup_image_candidates.py`.

[The exact path audit](verification/change-audit.json) lists all modified/new files, including this report, the three WebPs, mapping JSON and retained test artifacts. No existing files were deleted. Final fingerprints match across all 27 development collections and all index definitions; Git staging is unchanged. All 127 products and both Alpha Care placeholders remain unchanged in `iraseth_dev`. No commit, push, merge, reset, stash, backup or deployment occurred.

New documentation/assets/evidence: this directory's report, mapping proposal, three compressed WebPs and verification JSON/screenshots. No backend application route/service/model, dependency, environment file or MongoDB record was changed. No source file was deleted. Existing uncommitted work and Git staging remain preserved; no commit, push, merge or deployment occurred.

## Pending owner decision

The request explicitly requires authorization before development image writes. Approve the exact two-product mapping above before applying it to `iraseth_dev`. A later approved operation must use existing product validation/editing, preserve all other metadata, images, identities, quantities and prices, retain SKU/unit stock gates, and verify the two public galleries after the update. This task has prepared and tested the files; it has not applied those image updates.
