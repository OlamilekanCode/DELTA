# DELTA — Frontend

Next.js 16 App Router frontend for the DELTA stock↔crypto correlation platform.

## Stack

- **Next.js 16** (App Router, Turbopack)
- **TypeScript**
- **Tailwind CSS**
- **Framer Motion** — page and component animations
- **@xyflow/react** — interactive Exposure Graph (`/graph/[symbol]`)
- **lightweight-charts v5** — price history charts (`/asset/[symbol]`)
- **Reown AppKit + Wagmi + Viem** — wallet connection and `$DELTA` balance gating

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
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL, no trailing slash |
| `NEXT_PUBLIC_REOWN_PROJECT_ID` | Reown AppKit project ID (cloud.reown.com) |
| `NEXT_PUBLIC_DELTA_TOKEN_ADDRESS` | `$DELTA` ERC-20 contract address |
| `NEXT_PUBLIC_DELTA_MIN_BALANCE` | Minimum balance for portfolio access, in raw token base units |
| `NEXT_PUBLIC_DEX_BUY_URL` | DEX link for buying `$DELTA` |
| `NEXT_PUBLIC_CHAIN_ID` | Chain ID for the `$DELTA` token (default: 8453 — Base mainnet) |
| `NEXT_PUBLIC_SITE_URL` | Canonical public URL used in wallet metadata |

All `NEXT_PUBLIC_*` variables are embedded at build time and must be set before running `npm run build`.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/explore` | Asset grid with search and category/type filters |
| `/asset/[symbol]` | Price history chart and Exposure Scores for a single asset |
| `/graph/[symbol]` | Interactive radial Exposure Graph (React Flow) |
| `/portfolio` | Portfolio exposure analysis (requires `$DELTA` balance) |
| `/methodology` | Explanation of the Exposure Score calculation |

## Key components

- `components/explore/AssetGrid.tsx` — client-side filtered asset list
- `components/asset/AssetHistoryChart.tsx` — lightweight-charts v5, dynamically imported
- `components/asset/StockExposureList.tsx` — animated score cards with bar visualisation
- `components/graph/ExposureGraphCanvas.tsx` — React Flow graph with radial layout and score-filter slider
- `components/shared/FreshnessLabel.tsx` — demo (amber) vs live (green) data origin badge
- `components/wallet/PortfolioGate.tsx` — wallet connection and `$DELTA` balance gate

## SSR notes

`lightweight-charts` and `@xyflow/react` are browser-only. They are wrapped in client components (`AssetHistoryChartClient`, `ExposureGraphCanvasClient`) that use `next/dynamic` with `ssr: false`, so the parent Server Components can still fetch data on the server.

## Deployment (Vercel)

1. Set all `NEXT_PUBLIC_*` environment variables in the Vercel project settings.
2. Set the build command to `npm run build` and output to `.next`.
3. Set `NEXT_PUBLIC_API_BASE_URL` to your deployed backend URL.

The frontend has no server-side secrets — all API calls to the backend are made at request time from the browser or during static generation.
