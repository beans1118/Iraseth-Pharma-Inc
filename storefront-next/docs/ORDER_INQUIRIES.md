# Order Inquiries workflow

Orders and Order Inquiries remain separate dashboard menu items.

- New -> In Review, Accepted, or Declined.
- In Review -> New, Accepted, or Declined.
- Accepted and Declined are terminal. Repeating the same decision succeeds without another order or audit event.
- Existing Responded/Closed records remain readable and can be reviewed or decided; no migration rewrites records.
- All staff roles may read. Only superadmin/subadmin may change status, accept, or decline.

## Acceptance

POST /api/v2/quotations/<reference>/accept creates one Pending order in the existing orders collection and stores its ID on the inquiry. View Order opens the Orders list filtered to that ID. POST /decline declines without an order. PATCH /status uses the same transaction logic, including for Accepted/Declined.

Acceptance, the inquiry link/status, and its audit event commit together using MongoDB transactions. A partial unique orders.source_inquiry_id index permits multiple manual orders while enforcing one order per inquiry. Retryable transactions resolve concurrent decisions; repeated acceptance returns the original order ID. A replica set or sharded MongoDB deployment is required. Order-number gaps after rolled-back attempts are harmless.

Customer contact information, quantities, and notes transfer to the order. As with manual orders, official prices come from the current internal product catalog, not the public inquiry snapshot. The original public snapshot stays on the inquiry. Missing products or invalid prices reject acceptance without changing the inquiry. Acceptance does not reserve stock, deduct stock, or create invoices. Approval/fulfillment remain separate Orders actions and enforce stock eligibility there.

## Submission retries

The public endpoint compares normalized customer intent before looking up current products. Retries recover their existing reference even if products have since changed, become hidden, or gone out of stock. Older stored snapshot hashes are supported without migration. Reusing a key with different intent returns 409.

The storefront hashes normalized form/line data and saves retry keys in sessionStorage for that tab. Product metadata is excluded. Reloading and submitting the same customer details and cart reuses the key; altered details/quantities get a different key. Only hashes and keys are stored, not customer information. If retry storage is blocked, submission fails before sending. Form fields must be re-entered after reload; the existing cart persists independently. Retries from a different tab/browser do not share this key storage.

## Validation

From backend: .venv/Scripts/python.exe -m pytest tests/test_quotations_phase3.py tests/test_inquiry_acceptance.py tests/test_orders.py tests/test_order_fulfillment.py tests/test_order_status_transitions.py tests/test_public_catalog_phase2.py -q -p no:cacheprovider

Tests use the existing guarded iraseth_test replica-set fixture and remove only their own documents. Manual-order confirmation email is stubbed in the new regression test.

From storefront-next: npm run test:inquiries; npm run smoke; npm run syntax. Both frontend projects can be typechecked with tsc --noEmit --incremental false.
