# PDF products in the existing product system

Prepared 2026-11-16 on `feature/storefront-modernization`. **No development-database write is authorized or has been executed.**

Products use the existing `products` collection, `prepare_product` validation and `insert_product_document` persistence. Employees use **All Products → Edit metadata**, then **Batch Inventory → Receive stock**. Customers use the existing Flask `/api/public/products` API and Next.js `/products` pages. No additional public catalog, collection, route or management screen was added.

## Source and selection

The user previously approved the local `Core Product A5 (2).pdf` copy in place of the `(2)(1)` filename. Its SHA-256 is `4d1ac212740e739c6b5853231270cce2af22e66529916abc6835910b976a7696`.

- [Source-clear product list](source-clear-products.csv): **124** individually described candidates, with source page, category, source content, documented brand/model, image decision, missing fields, related source names and approval status. These are candidates for provisional creation, not 124 authorized live inserts.
- **11** individual candidates remain blocked by source conflicts/ambiguity; **131** families/offerings are excluded. The original manifest/review sheets remain intact.
- No candidate has a genuine staff SKU or selling unit yet. No manufacturer is documented. Leave missing manufacturer/model/content empty; a printed brand does not establish a manufacturer. Four candidates have documented model identifiers.
- [Image review](../brochure/pdf-product-image-review.json) includes **8** source images checked against named PDF panels. Two Alpha Care records have oversized images; Oncofusion's multi-configuration image is omitted. Other candidates without an individually approved image retain the ordinary placeholder. Existing upload limits apply.
- Related names are warnings, not proof of duplication or distinction. Exact matches stop creation. Possible matches within the database **and within the proposed batch** require a candidate-specific, documented duplicate review. Never approve related names in bulk merely to bypass a guard.

## Required identity behavior

The existing model requires `id` and `unit`. Provisional creation therefore uses `TMP-PDF-<source hash prefix>-<source candidate key>` as a **temporary internal product ID, not a genuine SKU**, and `PENDING UNIT CONFIRMATION` as an explicit unit marker, not a stock unit. `sku` stays empty and `identity_status` is `provisional`.

Quantity and baseline quantity are zero. Internal price and public price are null. Creation adds no stock batches, receipts, adjustments, reservations, orders or invoices. The ordinary visibility default publishes the zero-stock product as **Out of Stock / Price Upon Request**; customers cannot add it to My Order.

Receiving, release/allocation, adjustments, order acceptance/fulfillment and invoice creation are blocked for pending identity. Changing the description or replacing the unit text alone does not unlock stock operations. A public numeric price is also blocked while identity is pending.

An authorized Superadmin or Sub-admin confirms identity in the existing editor:

1. Locate the product in **All Products**, open **Edit metadata**, and compare its source record with supplier/staff records.
2. Edit descriptions, features, specifications and accurately matched images as needed. Leave identity confirmation unchecked for metadata-only edits.
3. Enter the genuine SKU and genuine selling unit. Check **I confirm this genuine SKU and selling unit from staff/supplier records** and record the supporting reference in **SKU/unit confirmation evidence**. Never use QA example values, guessed packaging or the temporary ID as the SKU.
4. Save. Server-side RBAC, normalized duplicate checks, a unique comparison-key index and transactional confirmation prevent duplicate SKU ownership. The audit records the actor and evidence. The internal ID, public URL and existing relationships stay stable.
5. Only after confirmation, use the existing **Receive stock** operation for actual delivered quantities, lot, expiry and reference. Identity confirmation creates no stock. Invoice selling prices must be entered explicitly. An unpriced order remains Price Upon Request rather than becoming a free order.

An Admin remains read-only. The existing product editor permits documented model/specification and image edits; it does not infer absent models or certify clinical claims.

## Exact read-only development dry run

Do not restart the updated Flask app against `iraseth_dev` merely to run a dry run: normal startup can ensure indexes. The standalone CLI imports the existing validation/service without starting Flask or creating indexes.

From the repository root in PowerShell, select this first batch of five clearly named, image-matched products:

| Candidate | Product | PDF page |
| --- | --- | --- |
| `p05-44c2375ce24d` | Microfusion Set | 5 |
| `p04-e228089cbacf` | Polyvol | 4 |
| `p06-2541990213ff` | Photofusion Set | 6 |
| `p07-303ca8b1c11b` | Blood Administration Set | 7 |
| `p07-f2a62b743ba6` | Haemofusor Set | 7 |

```powershell
$selected = @(
  '--candidate-id', 'p05-44c2375ce24d',
  '--candidate-id', 'p04-e228089cbacf',
  '--candidate-id', 'p06-2541990213ff',
  '--candidate-id', 'p07-303ca8b1c11b',
  '--candidate-id', 'p07-f2a62b743ba6'
)
backend\.venv\Scripts\python.exe backend\tools\add_pdf_products.py --database iraseth_dev @selected --report docs/pdf-products/dev-first-batch-dry-run-NEW.json
if ($LASTEXITCODE -ne 0) { throw 'Dry run failed; stop and resolve the reported issue.' }
```

The initial successful report is [dev-first-batch-dry-run.json](dev-first-batch-dry-run.json). Use a **new** report filename for each fresh run; the CLI refuses to overwrite review evidence. Check the database name, all five names/pages/IDs, descriptions/features/specifications, image counts, empty manufacturer/model where undocumented, null prices and zero quantity. No actor is needed for this read-only step. The CLI refuses remote/production MongoDB targets and never switches a mismatched environment configuration.

The report binds source, manifest, image-review, selections, product content and current catalog identities. Changes require a fresh dry run. Batches are limited to **1–30 distinct candidates**. For later possible duplicates, first investigate both products, then supply `--duplicate-reviewed-candidate-id <selected candidate>` and `--duplicate-review-note '<specific distinction and evidence>'` in both dry-run and apply commands. The flags do not override exact matches, source holds or identity collisions. If evidence is missing, leave the record out.

## Later apply operation — NOT authorized now

Before any write, obtain explicit owner authorization identifying the exact selected products and reviewed report, including the marked provisional identifiers/units and the required product-index changes. Verify the existing local target configuration, review current index compatibility and use an existing active Superadmin/Sub-admin actor. Do not create an account or invent staff approval.

Arrange a brief local maintenance window for that later operation. Close older backend/dashboard instances before applying: older running code may lack the identity gates. Resume staff access only with the updated backend and dashboard. Normal Flask startup can ensure additional indexes from existing local work; review/authorize those startup changes separately if needed. No development server was restarted or database schema changed during this task.

Only after that later authorization, in the same PowerShell session with the exact `$selected` array above and the freshly reviewed report:

```powershell
$staffEmail = 'REPLACE_WITH_EXISTING_AUTHORIZED_STAFF_EMAIL'
backend\.venv\Scripts\python.exe backend\tools\add_pdf_products.py --database iraseth_dev @selected --apply --confirm-database iraseth_dev --actor $staffEmail --reviewed-report docs/pdf-products/dev-first-batch-dry-run-NEW.json
if ($LASTEXITCODE -ne 0) { throw 'Apply failed or outcome uncertain; stop and inspect before retrying.' }
```

**Do not execute this apply command during the present task.** The permitted later operation ensures product `id`, `_sku_key` and `_brochure_identity` unique indexes, then atomically inserts only ordinary products and `catalog_events` audit entries. It creates no second product collection. Conflicting legacy index/data definitions cause failure; never repair them by deleting existing data. Already-created matching source IDs are skipped without overwriting staff edits; another product owning an ID stops the operation. A partially changed batch/catalog needs a fresh report, not an automatic retry with a new selection.

After an authorized apply, verify exactly five added source products (or documented skips), matching audit entries, quantity/baseline zero and null prices. Compare inventory batches, reservations, movements, adjustments, orders and invoices before/after. Search each product in Flask and Next.js, open its normal gallery/modal and standalone URL, and check existing filters/pagination. Receive real stock only after genuine identity confirmation. Do not import the remaining 119 or any held record without a separately reviewed and authorized batch.

## Verification

See [INTEGRATION-REPORT.md](INTEGRATION-REPORT.md) for checks, changes, development-database fingerprints and remaining blockers. All automated record changes were confined to `iraseth_test`; QA SKU/unit mappings and receipt/invoice examples are disposable simulations, never proposed live data.
