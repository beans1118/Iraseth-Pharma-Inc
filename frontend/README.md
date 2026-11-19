# Employee dashboard

Company installation, database initialization and isolated testing: [DEVELOPER-SETUP.md](../DEVELOPER-SETUP.md). Default local database: `iraseth`; both clients use the configured Flask API.

React, TypeScript and Vite dashboard backed by the existing Flask API. Products, metadata/gallery editing, inventory, inquiry decisions, orders, invoices, verified communications and staff permissions use the current API; this application has no database credentials.

The custom visual styling is TailAdmin-inspired; this repository does not contain or claim a licensed TailAdmin template. Sign-in tokens remain in `sessionStorage`, and Flask permissions remain authoritative.

From this directory, use Node 24 and `npm.cmd ci`, then `npm.cmd run dev` on Windows. Create `.env` from `.env.example` only if it is absent; preserve existing local settings. The development server defaults to port 5173 and proxies `/api` to `VITE_DEV_API_TARGET` (normally `http://127.0.0.1:5000`). A deployed build uses the public `VITE_API_BASE_URL` origin instead. Never put JWT, SMTP or MongoDB secrets in a Vite variable.

Run `npm.cmd run test:brochure`, `npm.cmd run test:deployment` and `npm.cmd run build` for mapping/configuration, TypeScript and production output. `dist/` is generated and ignored. Full browser UAT runs from `storefront-next/` against isolated local `iraseth_test`; see [the verification checklist](../docs/GITHUB-REVIEW-CHECKLIST.md).

For Vercel, project root is `frontend`, install is `npm ci`, build is `npm run build`, output is `dist`. `vercel.json` supplies SPA fallback. Use [the staging deployment plan](../docs/STAGING-DEPLOYMENT-PLAN.md); no deployment is authorized by these setup instructions.

The connected stock screens use `/api/v2/inventory/summary`, `/batches`, `/batches/receive`, `/release` and `/movements`; official-order actions use `/api/v2/orders/<id>/approve|fulfill|cancel`. Product metadata uses `/api/products`; public availability remains the public catalog's responsibility. Product creation starts at zero, and provisional identities cannot receive or reserve stock. Existing approved batch mode must pass readiness; do not enable it or run a migration merely to test the UI.

Large-inventory paging and advanced adjustment/reservation-detail, returns, quarantine and disposal UX still require separate review. Do not fabricate an adjustment queue when a listing API is unavailable. Inventory values come from Flask rather than frontend recalculation. Browser UAT now covers the operational workflows; independent accessibility/security review, real cloud HTTPS/CORS/mail delivery and stakeholder acceptance remain deployment gates. The application does not directly contact MongoDB or run migrations/seeding.
