# Iraseth Pharma Backend Improvements
## Phases 1–3 Detailed README

### Purpose

This document summarizes the backend improvements completed across Phases 1, 2, and 3 of the Iraseth Pharma inventory management system.

The goal of these phases was to improve the system without redesigning the current frontend. Most changes happen behind the interface and are intended to make the application safer, more reliable, more secure, and more scalable before production deployment.

> Status note: These changes were prepared as cumulative backend patches. Python syntax checks passed on the generated Phase 3 cumulative patch, but full local runtime and end-to-end testing should still be completed before committing and deploying.

---

# Phase 1
## Data Integrity and Inventory Safety

### Main Goal

Phase 1 focused on protecting the correctness of inventory and order data.

The original backend already supported products, inventory, orders, logs, users, and real-time updates, but several operations used a read-calculate-write pattern that could become unsafe when two requests happened at nearly the same time.

Phase 1 changed the critical stock and order operations so MongoDB becomes the final authority for inventory changes.

## 1. Atomic Inventory Release

### Before

The original flow was effectively:

1. Read current stock.
2. Calculate the new stock quantity.
3. Check if it would become negative.
4. Update the product.

This could create a race condition.

Example:

- Current stock: 10
- User A releases 6
- User B releases 6 at almost the same time

Both requests could read 10 before either update completed.

### After

Stock release uses an atomic MongoDB update with a condition that enough stock must still be available.

Conceptually:

```text
Find product where:
id = product_id
AND quantity >= requested quantity

Then:
quantity = quantity - requested quantity
```

### Effect

- Two users cannot spend the same remaining inventory.
- Stock cannot go below zero through the normal release endpoint.
- If there is not enough stock, the request is rejected.

Example:

```text
Stock = 10

Request A releases 6
Result: success
Remaining stock = 4

Request B releases 6
Result: rejected
Reason: only 4 remain
```

### User-visible effect

The interface does not change visually.

The user only sees a difference when trying to release more stock than is available. Instead of incorrect inventory, the system returns an error.

## 2. Atomic Restocking

### Before

Restocking changed the product quantity and also updated `baseline_qty`, which is used for low-stock calculations.

These values needed to remain synchronized.

### After

Restocking updates the quantity and the baseline as part of the protected database operation.

Example:

```text
Current quantity = 20
Supply added = 100

New quantity = 120
New baseline_qty = 120
```

### Effect

The low-stock calculation remains consistent with the latest full/restocked quantity.

## 3. Safe Order Fulfillment

### Before

When an order was marked Fulfilled, the old code deducted stock for each line item.

If the requested quantity was greater than available stock, the old logic could force the remaining quantity to zero instead of rejecting the fulfillment.

Example:

```text
Available stock = 3
Order quantity = 10

Old result:
Stock becomes 0
Order may still become Fulfilled
```

### After

The system verifies that enough stock is available before successfully completing fulfillment.

### Effect

If an order requires more stock than is available:

- fulfillment is rejected
- stock remains unchanged
- the order does not successfully complete fulfillment

## 4. All-or-Nothing Multi-Item Fulfillment

Order fulfillment uses a MongoDB transaction.

If one item in a multi-product order cannot be fulfilled, the entire transaction rolls back.

Example:

```text
Paracetamol x 5
Amoxicillin x 3
Vitamin C x 20
```

If Vitamin C has insufficient stock, none of the other deductions are saved.

### Important requirement

MongoDB transactions require MongoDB Atlas or another transaction-capable replica-set deployment.

## 5. Double-Fulfillment Protection

The backend now protects against the same order deducting stock twice because of:

- double clicks
- repeated requests
- two staff members fulfilling the same order at nearly the same time

## 6. Atomic Order Number Generation

Order IDs now use an atomic MongoDB counter.

Example:

```text
PO-20260035
PO-20260036
PO-20260037
```

Concurrent order creation no longer relies on simply reading the latest order and adding one.

## 7. Monthly Opening Snapshot Protection

Beginning-of-month stock snapshots are protected by a unique database rule based on:

```text
month + product_id
```

Only one monthly opening snapshot can exist for each product per month.

## 8. Duplicate Product Protection

MongoDB's unique product ID index is used as the final authority, and duplicate-key errors are handled cleanly.

## Phase 1 Files Updated

```text
extensions.py
products.py
inventory.py
orders.py
```

## Phase 1 Result

Phase 1 improves:

```text
Correctness
Data integrity
Concurrency safety
Inventory reliability
```

It does not redesign the frontend.

---

# Phase 2
## Security Hardening

### Main Goal

Phase 2 focused on strengthening authentication, API abuse protection, real-time connection security, and production configuration.

## 1. JWT Session Validation

The existing project already issued JWTs and stored a session record with a `jti`.

Phase 2 makes protected requests capable of checking the JWT against the active session record.

### Effect

A logged-out or revoked token can be rejected instead of remaining usable until its expiration time.

## 2. Login Rate Limiting

The login endpoint is protected against excessive repeated password attempts.

This reduces:

- brute-force risk
- credential-stuffing risk
- unnecessary bcrypt CPU load

## 3. Public Order Rate Limiting

The public order endpoint receives abuse protection to reduce:

- fake orders
- spam
- email abuse
- excessive database writes
- unnecessary backend load

## 4. API Rate Limiting for Sensitive Operations

Priority endpoints include:

```text
/api/auth/login
/api/orders
/api/inventory/*
/api/backup/*
```

This provides an application-level protection layer even before adding an external firewall/WAF.

## 5. Production CORS Restrictions

Production CORS is prepared to allow only approved frontend origins instead of wildcard browser access.

Example:

```text
https://project-name.vercel.app
```

## 6. Socket.IO Origin Restrictions

The original Socket.IO configuration allowed any origin.

Phase 2 prepares/restricts Socket.IO to approved frontend origins.

## 7. Socket.IO Authentication and Role Protection

The original room join handler only checked the requested room name.

Phase 2 adds/prepares authenticated room access.

Intended permissions:

```text
inventory room:
authenticated staff

logs room:
Superadmin and Admin
```

### Frontend note

This requires a small frontend integration so the existing JWT can be sent during the Socket.IO connection/join flow. It does not require a visual redesign.

## 8. Strong Production Secret Validation

Production should reject unsafe defaults such as:

```text
dev-secret-change-me
```

This reduces the chance of accidentally deploying with development secrets.

## 9. Default Credential Protection

Seed/default passwords should not be accepted as production credentials.

## 10. Security Headers

Phase 2 adds/prepares headers such as:

```text
Content-Security-Policy
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
Strict-Transport-Security
```

## 11. Trusted Proxy Handling

Because production will run behind Render and possibly Cloudflare, trusted proxy handling is prepared for correct client IP interpretation.

This matters for:

- rate limiting
- audit logs
- failed-login tracking
- security analysis

## 12. Readiness Check

The existing `/api/health` answers whether Flask is running.

Phase 2 adds/prepares a deeper readiness endpoint such as `/api/ready` to confirm that the application can also reach MongoDB.

## 13. Cloudflare / WAF Preparation

Cloudflare was discussed as an additional security layer, but it is intentionally deferred because no custom domain exists yet.

The system can still be tested and deployed using:

```text
Vercel default domain
Render default domain
```

Cloudflare can be added later when a custom domain is available.

## Phase 2 Result

Phase 2 improves:

```text
Authentication safety
Session control
API abuse protection
Real-time access control
Production security configuration
```

Most Phase 2 changes are intentionally invisible during normal use.

---

# Phase 3
## Backend Performance and Scalability

### Main Goal

Phase 3 focuses on keeping the backend responsive as products, orders, and audit logs increase.

The frontend design was intentionally preserved.

## 1. Batch Product Lookup During Checkout

### Before

An order with 20 line items could require up to 20 separate MongoDB product lookups.

### After

The backend:

1. collects the unique product IDs
2. performs one MongoDB `$in` query
3. creates a product lookup map
4. calculates the order from that result

### Effect

```text
20 order products
=
1 main product query
```

This removes the N+1 checkout query pattern.

## 2. Optional Product Pagination

Products support:

```text
/api/products?page=1&limit=50
```

Pagination is optional so the existing frontend can continue to work without changes.

Metadata can be returned in headers such as:

```text
X-Total-Count
X-Page
X-Page-Size
```

## 3. Optional Order Pagination

Orders support the same optional `page` and `limit` behavior.

This prevents future large order histories from requiring one huge response.

## 4. Log Pagination

Session and inventory audit logs support page/limit controls.

Invalid values such as:

```text
?page=test
```

return a controlled validation error rather than an unhandled server error.

## 5. Safer Search Queries

Search input is escaped before being used in MongoDB regular expressions.

ID searches can also be prefix-anchored where appropriate.

### Effect

Search behavior becomes more predictable and potentially more index-friendly.

## 6. MongoDB Connection Pool Configuration

The existing shared PyMongo client architecture is preserved.

Phase 3 adds configurable settings such as:

```text
MONGO_MAX_POOL_SIZE
MONGO_MIN_POOL_SIZE
MONGO_SERVER_SELECTION_TIMEOUT_MS
MONGO_CONNECT_TIMEOUT_MS
MONGO_SOCKET_TIMEOUT_MS
```

### Effect

MongoDB connections can be reused efficiently while timeout behavior remains configurable.

## 7. Asynchronous Email Dispatch

### Before

Order confirmation and status email were sent synchronously.

That meant the API could wait for:

```text
SMTP connection
TLS
Login
Email delivery
```

before responding.

### After

Email can be dispatched through a small background worker pool.

### Effect

The order/status API can return sooner without waiting for normal SMTP delivery.

## 8. SMTP Timeout

SMTP now has an explicit configurable timeout such as:

```text
SMTP_TIMEOUT_SECONDS=5
```

An unreachable email provider should not hang a request indefinitely.

## 9. Response Compression

Larger compressible responses, especially JSON, can be compressed before being sent over the network.

### Effect

Less data may need to travel between Render and the browser after deployment.

## 10. Maximum Order Line Limit

A configurable maximum order line count protects the public checkout endpoint from excessively large requests.

Example:

```text
MAX_ORDER_LINES=100
```

## 11. Existing Real-Time Design Preserved

Socket.IO remains the mechanism for pushing live inventory and log updates.

This supports:

```text
MongoDB update
   |
Socket.IO event
   |
Open dashboard updates
```

without requiring constant polling or a frontend redesign.

---

# Cumulative Effect of Phases 1–3

After the first three phases, the backend moves from a functional demo-style implementation toward a production-ready structure.

```text
Frontend
   |
Flask API
   |
   +-- Atomic inventory operations
   +-- Transactional fulfillment
   +-- Unique order IDs
   +-- Session-aware JWT security
   +-- Rate limiting
   +-- Protected Socket.IO design
   +-- Security headers
   +-- Readiness checking
   +-- Pagination support
   +-- Batched database queries
   +-- Connection pool tuning
   +-- Async email
   +-- Response compression
   |
MongoDB / MongoDB Atlas
```

# What Users Will Actually Notice

## Phase 1

Users may notice:

- releasing more stock than available is rejected
- insufficient-stock orders cannot be fulfilled
- repeated fulfillment does not deduct stock again
- simultaneous inventory activity is safer and more accurate

## Phase 2

Usually there is very little visual change.

Users may notice:

- revoked/invalid sessions require authentication again
- excessive login attempts can be throttled
- unauthorized actions are rejected correctly

## Phase 3

The main effect should be responsiveness and scalability:

- checkout performs fewer database queries
- large datasets can be loaded in smaller pages
- email does not need to delay the main API response
- larger responses can transfer more efficiently

# What We Intentionally Did Not Change

```text
Existing frontend visual design
HTML/CSS layout
Current dashboard appearance
Primary API route names
Role structure
General inventory workflow
General order workflow
```

The team liked the existing frontend, so the work focused on improving the backend underneath it.

---

# Known Frontend Item to Review Next

One authentication-state behavior was observed:

```text
Login as Superadmin
Refresh the page
Login screen appears
Click login
User goes through because the token/session still exists
```

This is not an intended Phase 1–3 feature.

The frontend should restore the session on page load.

Expected behavior:

```text
Refresh admin page
   |
Existing token?
   |
Call /api/auth/me
   |
Valid token -> open/keep dashboard
Invalid token -> clear session and show login
```

This will be handled during the frontend review.

---

# Testing and Commit Status

The generated cumulative Phase 3 backend patch passed Python syntax compilation checks.

However:

```text
Syntax check != full application test
```

Before committing:

1. Apply the cumulative Phase 3 patch locally.
2. Install the updated requirements.
3. Run the backend.
4. Test login/logout.
5. Test products.
6. Test release/supply.
7. Test insufficient-stock release.
8. Test valid fulfillment.
9. Test insufficient-stock fulfillment.
10. Test repeated fulfillment.
11. Test multiple order creation.
12. Test logs.
13. Test Socket.IO.
14. Test optional pagination.
15. Test readiness endpoint.
16. Test email behavior.
17. Verify MongoDB records.
18. Commit only after local tests pass.

---

# Next Step

After presenting Phases 1–3, the next review will focus on the frontend:

- session restoration after refresh
- Socket.IO token integration
- production API URL configuration
- production removal of mock fallback

After backend and frontend testing are complete, the project can move to Phase 4:

```text
Production Deployment
Vercel + Render + MongoDB Atlas
```
