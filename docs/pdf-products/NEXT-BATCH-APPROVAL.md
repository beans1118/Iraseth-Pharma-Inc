# Next PDF product batch — approval required

Prepared 2026-11-16 on `feature/storefront-modernization`. **No additional `iraseth_dev` writes are authorized or executed in this preparation task.** Only the following five products are proposed. Do not import the remaining candidates automatically.

## Current verified state

The active target is local MongoDB `127.0.0.1:27017`, database **`iraseth_dev`**, with `APP_ENV=development` and batch inventory enabled. The current catalog contains **8 products**: the original 3 and the first 5 PDF products. The original integration report/procedure describe the earlier preparation phase; the first five were subsequently authorized and inserted in the preceding task.

The five existing PDF products were verified against their original reviewed names, categories, descriptions, features and specifications. Their identities remain provisional, genuine SKU fields are empty, quantity/baseline quantity are zero, internal/public prices are null, manufacturer fields are blank, and each has its reviewed image. No stock batches or reservations exist for them. The development API and Next.js page still return/display the eight-product catalog.

Source: the previously user-approved local `Core Product A5 (2).pdf` copy, used in place of the `(2)(1)` filename. SHA-256: `4d1ac212740e739c6b5853231270cce2af22e66529916abc6835910b976a7696`. The CSV contains exactly the same 124 unique source-clear candidate keys as the manifest assessment. **119 source-clear candidates remain unimported.** The 11 source-conflicted items and 131 families/offerings remain excluded.

## Exact proposed five-product batch

| Product | Candidate key / PDF page | Provisional internal product ID | Image decision |
| --- | --- | --- | --- |
| Alpha Care Adult Diaper - XL | `p03-0dad68e8adcd` / 3 | `TMP-PDF-4D1AC21274-P03-0DAD68E8ADCD` | Placeholder; source PNG exceeds the existing 200,000-byte limit |
| Alpha Care Underpads - 60 cm x 90 cm | `p03-2d486f10f85e` / 3 | `TMP-PDF-4D1AC21274-P03-2D486F10F85E` | Placeholder; both source PNGs exceed the existing limit |
| Autofusion Set | `p05-694dfd26e1a4` / 5 | `TMP-PDF-4D1AC21274-P05-694DFD26E1A4` | One reviewed image: `images/autofusion.png` |
| Polyflex - 22G Blue | `p08-b9f2a7d02685` / 8 | `TMP-PDF-4D1AC21274-P08-B9F2A7D02685` | One reviewed image: `images/polyflex.png` |
| Polyflon - 20G Pink | `p09-e2c737e40d05` / 9 | `TMP-PDF-4D1AC21274-P09-E2C737E40D05` | One reviewed image: `images/polyflon.png` |

The first two products are Adult Care; Autofusion is Infusion and Transfusion; the two named cannula variants are IV Cannulas. Printed brands are Alpha Care and POLYMED respectively. No manufacturer or model identifier is inferred. Printed packaging specifications remain source metadata and do not establish an approved selling unit.

All five would use the existing product validator/service and `products` collection. Genuine `sku` remains empty, `identity_status` remains `provisional`, and `unit` is the explicit `PENDING UNIT CONFIRMATION` marker. Initial quantity and baseline are zero, internal/public price null, and the existing visibility default publishes them as Out of Stock / Price Upon Request. Stock receiving, release, reservation/allocation, fulfillment and other SKU-dependent operations remain blocked until genuine SKU/unit confirmation in the existing employee editor.

## Dry-run findings

[dev-next-batch-dry-run.json](dev-next-batch-dry-run.json) contains the exact descriptions, documented features/specifications, categories, image counts and bound source/catalog/content hashes for review.

- Proposed new records: **5**; selected records already present: **0**.
- Existing ID/SKU and normalized-name matches: **0**. Fuzzy/name-prefix matching against current products and the other selected records also passed without duplicate overrides.
- The first five already imported products were excluded from selection. No blind retry or second insertion was performed.
- Related Autofusion options and other cannula variants elsewhere in the source are not included. Their later selection must resolve any matches against the then-current catalog; this batch does not approve them.
- Every product remains source-clear. Oversized Alpha Care images are omitted; no upload limit is bypassed and no replacement image is invented.
- If authorized and successfully applied, the catalog would increase **8 → 13** and unimported source-clear candidates decrease **119 → 114**.

No Flask startup, index creation or database mutation was needed for the development dry run. Source, content, image review or catalog changes require a fresh dry run before apply.

## Verification completed before requesting approval

- **16 isolated backend tests passed** in `iraseth_test`, covering actual-PDF import/identity/duplicate/null-price behavior and the public catalog. Existing coverage includes SKU confirmation races, stock-operation blocking, ordinary editor confirmation and an unpriced inquiry/order/reservation/fulfillment/invoice flow.
- Existing Next.js pagination tests passed with 107 records, including categories after the first page and bounded upstream failures. Gallery interaction checks passed.
- This exact five-product batch was temporarily created through the same service in **`iraseth_test` only**. A repeat apply skipped all five without new records. Test stock, batches, orders, invoices and inventory audits did not change.
- Actual Flask API pagination was checked with page size 2. All five test products appeared exactly once; browser checks passed for their ordinary Next.js cards, modal galleries/placeholders, source text/features, standalone URLs, Out of Stock, Price Upon Request and disabled Add to My Order.
- The live development page and paginated API were inspected with GET requests only: still **8** products; none of the proposed five is present. No browser runtime errors occurred.
- All temporary five-product fixtures, their creation audit entries and their disposable test actor were removed. The tested collections returned to their pre-fixture fingerprints.

## Approval boundary

**Inserted into development in this task: 0. Failures: none.** Existing product data, stock, batches, reservations, orders, invoices, prices, audits and index definitions are preserved. Existing files and Git staging are preserved; only this review document and the new batch dry-run JSON are added. No application code or product screens were changed. No commit, push, deployment, reset, backup or source deletion was performed.

Owner approval must identify **only these five**, including the two placeholder image decisions and the provisional SKU/unit restriction. An approval of this batch does not authorize the other 114 candidates, any source-conflicted record, or any stock/price change. Apply remains behind the existing target/actor/report checks and transaction. Use an existing active authorized staff actor; do not create one or invent staff approval.

The precise selected arguments for a later authorized operation are:

```powershell
$selected = @(
  '--candidate-id', 'p03-0dad68e8adcd',
  '--candidate-id', 'p03-2d486f10f85e',
  '--candidate-id', 'p05-694dfd26e1a4',
  '--candidate-id', 'p08-b9f2a7d02685',
  '--candidate-id', 'p09-e2c737e40d05'
)
```

After explicit approval, refresh/review the dry run if anything has changed, then use the existing `add_pdf_products.py` workflow with this selection, `--database iraseth_dev`, the existing authorized `--actor`, `--apply --confirm-database iraseth_dev`, and `--reviewed-report docs/pdf-products/dev-next-batch-dry-run.json`. **Do not execute apply before owner approval.** Verify exactly the approved additions and creation audit events, preserve all prior records, and inspect the live API/storefront again before proposing another batch of at most five.
