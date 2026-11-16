# Storefront UX refinement — partner logos + conversational FAQ

## Implemented in the isolated Next.js storefront

- **My Order** is now an outlined blue rounded-rectangle button with the words “My Order” inside. It has keyboard focus/hover/active styles.
- The company logo remains in the **header** but is removed from the **footer**.
- Mobile navigation remains a full-height portal drawer with clearer stacking, tap states, Escape closing and scroll lock.
- **Connected by Care** now lives **within the Home page Explore Our Offerings section, immediately below the category cards**, before Featured Products.
- The moving carousel uses **logo-image slots**, not generic medical-sector names. Actual partner images are configured in `lib/partners.ts` and stored in `public/partners/`.
- With no approved logos, development mode displays deliberately labeled sample slots. Production omits the entire partner block until actual logos are configured; it never invents partners or displays sample logos as endorsements.
- The floating message button opens a **chat-style FAQ** with alternating visitor/assistant bubbles, clickable suggested FAQ questions, a free-text question input, deterministic keyword answers and a Contact fallback. It **does not** send messages to staff or use an AI backend. The interface clearly identifies itself as an automated FAQ and asks visitors not to share private data.
- The product-category implementation disclaimer remains removed.
- The floating cart still opens the existing order drawer and shows the item count.

## Future work (not implemented by this UI update)

1. Approve and provide actual partner logo files; register them in `lib/partners.ts`. Confirm brand display permission.
2. Add a public Flask catalog API with eligible batch inventory availability, automatic publication, an audited separate public price, and RBAC-checked staff updates; do not use the protected employee product listing as the public API.
3. Build real quotation-request submission with durable reference numbers, spam and rate-limit safeguards, and staff review. Submission must not reserve or deduct inventory.
4. Connect actual order-linked customer support separately; the FAQ assistant must not claim to be a live agent or accept orders.
5. Deploy Next.js on Vercel, Flask on Render, MongoDB in a separate UAT replica set, only after required security and regression tests. Do not expose the local `rs0` database to the internet.
6. Keep `backend/tests/` and `storefront-next/tests/`. Do not delete existing legacy/storefront folders until the replacement has been fully tested and migration references are checked.

## Validation

- `npm run smoke` and `npm run syntax` are available as source-level checks.
- `npm run typecheck` and `npm run build` must be run on the user's Windows machine with dependencies installed; they could not be completed in the package workspace.
- Test the chat and navigation at desktop and narrow mobile widths (e.g. 360px and 390px), including keyboard input and Escape.
