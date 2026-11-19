# Public storefront

Next.js storefront connected to the existing Flask public catalog, inquiry and tracking APIs. Product cards, search/category/brand/stock filters, pagination, galleries, shareable product URLs, My Order and reference tracking read live API data. No product list or inventory is hardcoded here.

Use Node 24 and `npm.cmd ci` from this directory on Windows. Create `.env` from `.env.example` only if absent; preserve existing settings. `CATALOG_API_BASE_URL` is the server-only Flask origin. `NEXT_PUBLIC_STAFF_LOGIN_URL` is the public dashboard origin. Never put MongoDB, SMTP or employee JWT secrets in frontend variables.

Run `npm.cmd run dev` locally on port 3000. Verification is `npm.cmd run typecheck`, `npm.cmd test` (includes smoke checks), and `npm.cmd run build`. Stop other Next processes sharing `.next` before a production rebuild. Browser UAT creates disposable records in local `iraseth_test` only; use [the checklist](../docs/GITHUB-REVIEW-CHECKLIST.md).

Vercel project root is `storefront-next`, install is `npm ci`, build is `npm run build`, framework is Next.js with default output. SSR and proxy route handlers are required; do not export a static site. See [the staging deployment plan](../docs/STAGING-DEPLOYMENT-PLAN.md) for exact origins and required settings.

Product galleries persist as MongoDB data, so cloning/pushing Git does not transfer the 127 local catalog records or their images to staging. Source PDF/media and approved image evidence remain in `docs/`. The current company images are versioned in `public/brand/`. Source content provenance and publication checks remain in [the storefront documents](docs/README.md).
