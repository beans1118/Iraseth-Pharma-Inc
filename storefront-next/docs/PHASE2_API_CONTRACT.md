# Proposed Phase 2 public catalog API contract (NOT IMPLEMENTED)

## `GET /api/public/products`

Successful response (schema only; this is not live or demo stock):

```json
{
  "products": [
    {
      "id": "<opaque stable product id>",
      "slug": "<unique url-friendly slug>",
      "name": "<catalog product name>",
      "category": "<category label>",
      "brand": "<optional manufacturer>",
      "description": "<approved public description>",
      "imageUrl": "<approved public image url>",
      "publicPrice": null,
      "inStock": false,
      "publishedAt": "<ISO 8601 timestamp>"
    }
  ]
}
```

`publicPrice` is a nonnegative PHP amount or `null` (show Price Upon Request). `inStock` must be calculated by Flask from eligible batch availability after expiry, restrictions, and reservations. The API should show only products approved for public listing (new eligible products published automatically, with an employee hide/unpublish override). Do not expose actual internal stock quantities, batch records, cost basis, deleted/archived catalog entries, or user data.

Do not publicly read the protected employee `GET /api/products`. Do not trust cached client cart availability at quotation submission. Server must revalidate every line when Phase 3 is implemented. Do not reuse invoice selling prices without explicit policy review, and do not derive VAT/tax claims by assumption.

Potential future endpoints (need implementation and tests): staff-controlled publishing/pricing update; public quotation submission with idempotency and rate limiting; authenticated staff quotation review. This file is intentionally a proposed contract, not evidence of implemented backend functionality.
