# Synthetic Exposure — Frontend

Next.js 16 App Router frontend for the Synthetic Exposure stock↔crypto correlation platform.

## Stack

- **Next.js 16** (App Router, Turbopack)
- **TypeScript**
- **Tailwind CSS**
- **Framer Motion** — page and component animations
- **@xyflow/react** — interactive Exposure Graph (`/graph/[symbol]`)
- **lightweight-charts v5** — price history charts (`/asset/[symbol]`)
- **Reown AppKit + Wagmi + Viem** — wallet connection, backed by server-side SIWE authentication (no client-only balance gating)

## Local setup

```bash
cd web
npm install
cp ../.env.example .env.local
# Set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 (or your backend URL)
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Commands

```bash
npm run dev           # development server (Turbopack)
npm run build         # production build
npm start             # serve the production build
npm run lint          # ESLint
npx tsc --noEmit      # TypeScript type-check
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL for public data, no trailing slash |
| `NEXT_PUBLIC_REOWN_PROJECT_ID` | Reown AppKit project ID (cloud.reown.com) |
| `NEXT_PUBLIC_SYNTHEX_CHAIN_ID` | Robinhood Chain ID for wallet prompts (display only — the backend enforces access) |
| `NEXT_PUBLIC_SYNTHEX_RPC_URL` | Public RPC for wallet-facing chain-add prompts — separate from the private, server-only `ROBINHOOD_RPC_URL` |
| `NEXT_PUBLIC_SYNTHEX_TOKEN_ADDRESS` | `$SynthEx` ERC-20 contract address (display only) |
| `NEXT_PUBLIC_SYNTHEX_BUY_URL` | DEX link for buying `$SynthEx` |
| `NEXT_PUBLIC_SITE_URL` | Canonical public URL used in wallet metadata |
| `BACKEND_API_URL` | Server-only (not `NEXT_PUBLIC_`) — FastAPI origin used by Next.js route handlers and Server Components for authenticated requests |

All `NEXT_PUBLIC_*` variables are embedded at build time and must be set before running `npm run build`. Holder access, tier and portfolio decisions are always enforced server-side — these public values are for display and wallet prompts only.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/explore` | Asset grid with search and category/type filters |
| `/asset/[symbol]` | Price history chart and Exposure Scores for a single asset |
| `/graph/[symbol]` | Interactive radial Exposure Graph (React Flow) |
| `/portfolio` | Portfolio exposure analysis (requires `$SynthEx` balance) |
| `/methodology` | Explanation of the Exposure Score calculation |

## Key components

- `components/explore/AssetGrid.tsx` — client-side filtered asset list
- `components/asset/AssetHistoryChart.tsx` — lightweight-charts v5, dynamically imported
- `components/asset/StockExposureList.tsx` — historical (90-day) Exposure Score cards
- `components/asset/LiveExposureSection.tsx` — live (30-min) Exposure Score section, polls `/api/intraday/[symbol]`
- `components/graph/ExposureGraphCanvas.tsx` — React Flow graph with radial layout and score-filter slider
- `components/shared/FreshnessLabel.tsx` — demo (amber) vs live (green) data origin badge
- `components/wallet/WalletStateManager.tsx` — the 10-state wallet/session/tier state machine (context provider)
- `components/wallet/ConnectWalletButton.tsx` — connect button, shows `$SynthEx` balance once authenticated
- `components/portfolio/PortfolioExposure.tsx` — renders the correct UI for every wallet state

## SSR notes

`lightweight-charts` and `@xyflow/react` are browser-only. They are wrapped in client components (`AssetHistoryChartClient`, `ExposureGraphCanvasClient`) that use `next/dynamic` with `ssr: false`, so the parent Server Components can still fetch data on the server.

## Deployment (Vercel)

1. Set all `NEXT_PUBLIC_*` environment variables in the Vercel project settings.
2. Set `BACKEND_API_URL` (server-only) to the Render API origin.
3. Set the build command to `npm run build` and output to `.next`.
