# Iraseth Pharma — React Inventory Console (Stage 5)

A working **frontend development candidate** for the existing Flask API. The visual language is TailAdmin-inspired, but this package uses custom styling: **it does not include or claim to be licensed TailAdmin source code**.

## Getting started (Windows PowerShell)

1. Keep Flask running at `http://127.0.0.1:5000` with the approved local batch mode (`BATCH_MODE=true`).
2. Place this **entire** folder at `Iraseth-Pharma-Inc/frontend/`, next to `backend/`. Do not paste it inside `backend/`.
3. In a **new** PowerShell window:

```powershell
cd C:\Users\JEdgie\Desktop\Iraseth-Pharma-Inc\frontend
npm install
npm run dev
```

4. Open `http://127.0.0.1:5173` and sign in with a staff account already stored in your backend. No credentials are included here.
5. Before committing, run `npm run build` and inspect `git status`.

Vite forwards all `/api` requests to Flask, so local development avoids CORS complications. To use a different Flask host, copy `.env.example` to `.env.local` and change `VITE_DEV_API_TARGET`. Restart Vite after changing it. Never put a JWT secret in Vite environment files.

## Connected screens

| Screen | Endpoints | Notes |
|---|---|---|
| Sign in / sign out | `/api/auth/login`, `/api/auth/me`, `/api/auth/logout` | Token in **sessionStorage**; reset when browser tab is closed. For production consider HttpOnly cookie-based auth. |
| Overview | `/api/products`, `/api/v2/inventory/summary`, `/api/orders`, `/api/v2/inventory/batches`, `/api/ready` | Live data, no fake demo records. |
| Products | `/api/products` | Superadmin can create products (zero initial quantity). |
| Batches | `/api/v2/inventory/batches`, `/api/v2/inventory/batches/receive`, `/api/v2/inventory/release` | Receive and manually release with idempotency keys. |
| Orders | `/api/orders`, `/api/v2/orders/:id/approve|fulfill|cancel` | Order creation is public on the current Flask backend, though the console requires staff login. |
| Stock movements | `/api/v2/inventory/movements` | Latest 100, read-only. |
| Adjustments | `/api/v2/inventory/adjustments`, `/api/v2/inventory/adjustments/:id/decision` | Subadmin can request; Superadmin can decide by ID. **No adjustment listing API exists yet**, so no pending queue is fabricated. |
| Team & access | `/api/users` | Superadmin-only list and create. |

## Known limitations / next stage

- This package is **not official TailAdmin**. To adopt its actual components/template, provide the licensed TailAdmin project/assets and we can integrate them instead.
- No automatic batch-mode readiness indicator: the UI assumes the approved `/api/v2` APIs are available and shows backend errors otherwise.
- This is Stage 5 + initial API integration. It is **not final production UX**. No pagination beyond the backend's first 100 batches/movements; add server-driven pagination when inventories grow.
- Adjustment listing/detail, batch reservation detail, customer management, returns, quarantine/restrict and disposal administration need UX and, for some workflows, additional backend endpoints.
- Inventory API values are reported by backend without frontend re-calculation. The frontend cannot enforce security; Flask's role checks remain authoritative.
- No UI component test suite has been run here; test the flows against your local instance, and add React Testing Library/Playwright before launch.
- Render/Vercel/Cloudflare deployment, production HTTPS/CORS, browser security, accessibility audit, error telemetry and real-user acceptance testing remain pending.

## Safety

Use development data only. Never execute migration scripts or seed data just to test the frontend. The frontend never directly contacts MongoDB.
