"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSwitchChain } from "wagmi";
import { useWalletState } from "@/components/wallet/WalletStateManager";
import ConnectWalletButton from "@/components/wallet/ConnectWalletButton";
import { formatScore } from "@/lib/format";
import type { ApiAsset } from "@/lib/types";

const DEX_URL = process.env.NEXT_PUBLIC_SYNTHEX_BUY_URL ?? "";
const TIER_LABELS: Record<string, string> = {
  summary: "Summary", detailed: "Detailed", premium: "Premium",
};
const COMING_SOON_LABELS: Record<string, string> = {
  advanced_graphs: "Advanced graphs",
  longer_portfolio_history: "Longer portfolio history",
  alerts: "Alerts",
};

function Shell({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
      {icon}
      <h1 className="font-heading text-3xl font-bold text-text sm:text-4xl">{title}</h1>
      {children}
    </div>
  );
}

// Literal class strings per color — Tailwind can't see runtime-interpolated
// class names, so every color variant must be spelled out in full here.
const ICON_COLOR_CLASSES = {
  "violet-light": { bg: "bg-violet-light/10", text: "text-violet-light" },
  amber: { bg: "bg-amber/10", text: "text-amber" },
  green: { bg: "bg-green/10", text: "text-green" },
} as const;

function Icon({ color, path }: { color: keyof typeof ICON_COLOR_CLASSES; path: string }) {
  const classes = ICON_COLOR_CLASSES[color];
  return (
    <div className={`flex size-16 items-center justify-center rounded-2xl ${classes.bg}`}>
      <svg className={`size-8 ${classes.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d={path} />
      </svg>
    </div>
  );
}

const WALLET_PATH = "M21 12a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 12m18 0v5.25A2.25 2.25 0 0 1 18.75 19.5H5.25A2.25 2.25 0 0 1 3 17.25V12m18 0V6.75A2.25 2.25 0 0 0 18.75 4.5H5.25A2.25 2.25 0 0 0 3 6.75V12";
const TOKEN_PATH = "M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125";
const CHECK_PATH = "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z";
const WARN_PATH = "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z";

export default function PortfolioExposure({ stocks }: { stocks: ApiAsset[] }) {
  const { state, entitlements, signInError, signingIn, signIn, configuredChainId, connectedChainId } = useWalletState();
  const { switchChain, isPending: switching } = useSwitchChain();
  const [switchError, setSwitchError] = useState<string | null>(null);

  switch (state) {
    case "disconnected":
      return (
        <Shell icon={<Icon color="violet-light" path={WALLET_PATH} />} title="Portfolio Exposure">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            Connect your wallet to check your $SynthEx balance and unlock portfolio exposure analysis.
          </p>
          <ConnectWalletButton className="px-6 py-3 text-base" />
        </Shell>
      );

    case "config_unavailable":
      return (
        <Shell icon={<Icon color="amber" path={WARN_PATH} />} title="Wallet Features Unavailable">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            Robinhood Chain configuration is not available yet. Portfolio access will unlock once it is.
          </p>
        </Shell>
      );

    case "wrong_chain":
      return (
        <Shell icon={<Icon color="amber" path={WARN_PATH} />} title="Wrong Network">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            Switch your wallet to Robinhood Chain to continue.
          </p>
          <button
            type="button"
            disabled={switching || !configuredChainId}
            onClick={() => {
              setSwitchError(null);
              if (!configuredChainId) return;
              switchChain(
                { chainId: configuredChainId },
                { onError: (e) => setSwitchError(e.message) }
              );
            }}
            className="inline-flex items-center gap-2 rounded-xl bg-violet px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet/90 active:scale-95 disabled:opacity-50"
          >
            {switching ? "Switching…" : "Switch to Robinhood Chain"}
          </button>
          {switchError && (
            <p className="max-w-sm font-mono text-xs text-red-400">
              Couldn&apos;t switch automatically — add Robinhood Chain in your wallet manually.
            </p>
          )}
          <p className="font-mono text-[10px] text-muted/50">
            Connected chain {connectedChainId ?? "unknown"} · Required {configuredChainId}
          </p>
        </Shell>
      );

    case "unauthenticated":
      return (
        <Shell icon={<Icon color="violet-light" path={WALLET_PATH} />} title="Sign In With Wallet">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            Sign a free message to verify wallet ownership. No gas, no token approval, no blockchain transaction.
          </p>
          <button
            type="button"
            disabled={signingIn}
            onClick={() => signIn()}
            className="inline-flex items-center gap-2 rounded-xl bg-violet px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet/90 active:scale-95 disabled:opacity-50"
          >
            {signingIn ? "Waiting for signature…" : "Sign In With Wallet"}
          </button>
          {signInError && <p className="max-w-sm font-mono text-xs text-red-400">{signInError}</p>}
        </Shell>
      );

    case "loading":
      return (
        <Shell icon={<div className="size-16 animate-pulse rounded-2xl bg-panel2" />} title="Loading…">
          <div className="h-4 w-48 animate-pulse rounded bg-panel2" />
        </Shell>
      );

    case "no_token":
      return (
        <Shell icon={<Icon color="amber" path={TOKEN_PATH} />} title="$SynthEx Required">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            Portfolio exposure analysis is available to $SynthEx token holders. Acquire $SynthEx to unlock access.
          </p>
          {DEX_URL && (
            <a
              href={DEX_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-violet px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet/90 active:scale-95"
            >
              Get $SynthEx
            </a>
          )}
          <div className="w-full max-w-md"><PurchaseVerificationForm /></div>
        </Shell>
      );

    case "insufficient_balance":
      return (
        <Shell icon={<Icon color="amber" path={WARN_PATH} />} title="Balance Below Requirement">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            Your current $SynthEx balance no longer meets the holder requirement, so portfolio access is
            suspended. Restoring your balance restores access — no new purchase is required unless you want
            to upgrade tier.
          </p>
          {(entitlements?.synthex_balance != null || entitlements?.synthex_required_balance != null) && (
            <p className="font-mono text-xs text-text">
              Current: <span className="font-bold">{entitlements?.synthex_balance ?? "—"}</span> SynthEx
              {entitlements?.synthex_required_balance != null && (
                <> · Required: <span className="font-bold">{entitlements.synthex_required_balance}</span> SynthEx</>
              )}
            </p>
          )}
          {DEX_URL && (
            <a
              href={DEX_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-violet px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet/90 active:scale-95"
            >
              Get $SynthEx
            </a>
          )}
          <div className="w-full max-w-md"><PurchaseVerificationForm /></div>
        </Shell>
      );

    case "holder_locked":
      return (
        <Shell icon={<Icon color="green" path={CHECK_PATH} />} title="Portfolio Locked">
          <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
            You&apos;re a verified $SynthEx holder. Purchase $50+ of $SynthEx (cumulative) to unlock portfolio
            exposure summary.
          </p>
          {DEX_URL && (
            <a
              href={DEX_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-violet px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet/90 active:scale-95"
            >
              Buy $SynthEx
            </a>
          )}
          <div className="w-full max-w-md"><PurchaseVerificationForm /></div>
        </Shell>
      );

    case "tier_summary":
    case "tier_detailed":
    case "tier_premium":
      return <PortfolioDetail tier={state} entitlements={entitlements} stocks={stocks} />;

    default:
      return null;
  }
}

interface PortfolioHolding {
  symbol: string;
  usd_value: number;
  pct_of_portfolio: number;
}

interface PortfolioExposureResponse {
  portfolio_exposure_score: number | null;
  note?: string;
  stock?: string;
  stocks_covered?: number;
  assets?: { symbol: string; weight: number; score?: number }[];
  excluded?: { symbol?: string; contract_address?: string; reason: string }[];
  ranked?: { stock: string; portfolio_exposure_score: number; assets: { symbol: string; weight: number; score: number }[] }[];
  // Intraday counterpart of the figures above — calculated separately from
  // the historical (90-day) figures, never blended into them.
  live_portfolio_exposure_score?: number | null;
  live_status?: "ready" | "collecting_data" | "no_data";
  live_stocks_covered?: number;
  live_ranked?: { stock: string; portfolio_exposure_score: number; assets: { symbol: string; weight: number; score: number }[] }[];
  category_exposure?: { category: string; weight: number }[];
  coming_soon?: string[];
  data_ts?: string | null;
  positions_stale?: boolean;
  quotes_stale?: boolean;
  total_usd_value?: number;
  supported_position_count?: number;
  excluded_position_count?: number;
  // Direct (Robinhood Stock Token) exposure — literal ownership, never
  // blended into portfolio_exposure_score's correlation-based figure.
  direct_exposure_usd?: number;
  direct_exposure_pct?: number;
  direct_holdings?: PortfolioHolding[];
  direct_holding_for_stock?: PortfolioHolding | null;
  // Cash (stablecoin) allocation — zero correlation, still counted in the
  // total-USD denominator above.
  cash_usd?: number;
  cash_pct?: number;
  cash_holdings?: PortfolioHolding[];
}

interface PortfolioRefreshResponse {
  status: "ok" | "not_configured";
  chains_attempted: number;
  contracts_attempted: number;
  positions_refreshed: number;
  skipped: number;
  failed: number;
  message: string | null;
}

type RefreshState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; result: PortfolioRefreshResponse }
  | { kind: "partial"; result: PortfolioRefreshResponse }
  | { kind: "not_configured"; result: PortfolioRefreshResponse }
  | { kind: "error"; message: string };

function RefreshWalletAssetsControl({ onRefreshed }: { onRefreshed: () => void }) {
  const [refreshState, setRefreshState] = useState<RefreshState>({ kind: "idle" });

  async function handleRefresh() {
    setRefreshState({ kind: "loading" });
    try {
      const res = await fetch("/api/portfolio/refresh", { method: "POST" });
      const body = (await res.json().catch(() => null)) as PortfolioRefreshResponse | null;
      if (!res.ok || !body) {
        setRefreshState({ kind: "error", message: "Couldn't refresh wallet assets — try again shortly." });
        return;
      }
      if (body.status === "not_configured") {
        setRefreshState({ kind: "not_configured", result: body });
        return;
      }
      setRefreshState({ kind: body.failed > 0 || body.skipped > 0 ? "partial" : "success", result: body });
      onRefreshed();
    } catch {
      setRefreshState({ kind: "error", message: "Couldn't refresh wallet assets — try again shortly." });
    }
  }

  return (
    <div className="mb-4 flex flex-wrap items-center gap-3">
      <button
        type="button"
        disabled={refreshState.kind === "loading"}
        onClick={handleRefresh}
        className="inline-flex items-center gap-2 rounded-xl border border-white/[0.09] bg-panel2 px-4 py-2 font-mono text-xs font-bold text-text transition-all hover:bg-panel2/70 active:scale-95 disabled:opacity-50"
      >
        {refreshState.kind === "loading" ? "Refreshing…" : "Refresh wallet assets"}
      </button>
      {refreshState.kind === "success" && (
        <span className="font-mono text-xs text-green">
          {refreshState.result.positions_refreshed} position{refreshState.result.positions_refreshed === 1 ? "" : "s"} refreshed
        </span>
      )}
      {refreshState.kind === "partial" && (
        <span className="font-mono text-xs text-amber">
          {refreshState.result.positions_refreshed} refreshed · {refreshState.result.skipped} skipped · {refreshState.result.failed} failed
        </span>
      )}
      {refreshState.kind === "not_configured" && (
        <span className="font-mono text-xs text-muted">
          Wallet refresh isn&apos;t configured yet{refreshState.result.message ? ` — ${refreshState.result.message}` : ""}.
        </span>
      )}
      {refreshState.kind === "error" && (
        <span className="font-mono text-xs text-red-400">{refreshState.message}</span>
      )}
    </div>
  );
}

const TX_HASH_RE = /^0x[a-fA-F0-9]{64}$/;

interface VerifyPurchaseResponse {
  status: string;
  message?: string | null;
  tier?: string;
  cumulative_usd?: number;
  usd_value?: number;
}

const PURCHASE_STATUS_LABELS: Record<string, string> = {
  not_configured: "Purchase verification isn't configured yet.",
  invalid: "This transaction couldn't be verified.",
  pending: "Waiting for more confirmations — try again shortly.",
  already_claimed: "This transaction has already been claimed.",
  price_unavailable: "No ETH/USD price is available for this transaction's time yet — try again shortly.",
  unsupported_purchase_method: "This purchase method isn't supported for verification yet.",
  unable_to_determine_net_spend: "Couldn't determine how much ETH/WETH was spent on this transaction.",
  rpc_error: "Network error while verifying — try again shortly.",
};

function PurchaseVerificationForm() {
  const queryClient = useQueryClient();
  const [txHash, setTxHash] = useState("");
  const [state, setState] = useState<
    { kind: "idle" } | { kind: "loading" } | { kind: "result"; result: VerifyPurchaseResponse }
  >({ kind: "idle" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = txHash.trim();
    if (!TX_HASH_RE.test(trimmed)) {
      setState({
        kind: "result",
        result: { status: "invalid", message: "Enter a valid transaction hash (0x followed by 64 hex characters)." },
      });
      return;
    }
    setState({ kind: "loading" });
    try {
      const res = await fetch("/api/entitlements/verify-purchase", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tx_hash: trimmed }),
      });
      const body = (await res.json().catch(() => null)) as VerifyPurchaseResponse | null;
      if (!body) {
        setState({ kind: "result", result: { status: "error", message: "Couldn't reach the server — try again shortly." } });
        return;
      }
      setState({ kind: "result", result: body });
      if (body.status === "verified") {
        setTxHash("");
        queryClient.invalidateQueries({ queryKey: ["entitlements-status"] });
        queryClient.invalidateQueries({ queryKey: ["portfolio-exposure"] });
      }
    } catch {
      setState({ kind: "result", result: { status: "error", message: "Couldn't reach the server — try again shortly." } });
    }
  }

  const result = state.kind === "result" ? state.result : null;
  const toneClass =
    result?.status === "verified"
      ? "text-green"
      : result?.status === "pending" || result?.status === "already_claimed" || result?.status === "price_unavailable"
        ? "text-amber"
        : "text-red-400";

  return (
    <div className="rounded-2xl border border-white/[0.09] bg-panel p-6 text-left">
      <p className="mb-1 font-mono text-xs uppercase tracking-widest text-muted">Verify a $SynthEx Purchase</p>
      <p className="mb-3 font-mono text-xs text-muted/70">
        Paste the transaction hash of your $SynthEx/ETH purchase to unlock or upgrade your tier.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={txHash}
          onChange={(e) => setTxHash(e.target.value)}
          placeholder="0x…"
          spellCheck={false}
          className="flex-1 rounded-xl border border-white/[0.09] bg-panel2 px-3 py-2 font-mono text-sm text-text focus:border-violet focus:outline-none"
        />
        <button
          type="submit"
          disabled={state.kind === "loading" || !txHash.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-violet px-4 py-2 font-mono text-xs font-bold text-white transition-all hover:bg-violet/90 active:scale-95 disabled:opacity-50"
        >
          {state.kind === "loading" ? "Verifying…" : "Verify Purchase"}
        </button>
      </form>
      {result && (
        <p className={`mt-3 font-mono text-xs ${toneClass}`}>
          {result.status === "verified"
            ? `Verified — tier is now ${TIER_LABELS[result.tier ?? ""] ?? result.tier}.`
            : (PURCHASE_STATUS_LABELS[result.status] ?? result.message ?? "Verification failed.")}
        </p>
      )}
    </div>
  );
}

function PortfolioDetail({
  tier,
  entitlements,
  stocks,
}: {
  tier: "tier_summary" | "tier_detailed" | "tier_premium";
  entitlements: { tier: string; cumulative_usd: number } | null;
  stocks: ApiAsset[];
}) {
  const showDetailed = tier === "tier_detailed" || tier === "tier_premium";
  const showComingSoon = tier === "tier_premium";
  const queryClient = useQueryClient();
  const [selectedStock, setSelectedStock] = useState("");

  const { data: exposure, error: exposureError, isLoading } = useQuery({
    queryKey: ["portfolio-exposure", selectedStock],
    queryFn: async () => {
      const qs = selectedStock ? `?stock=${encodeURIComponent(selectedStock)}` : "";
      const res = await fetch(`/api/portfolio/exposure${qs}`, { cache: "no-store" });
      // A failed request is a real backend/network error, not an empty
      // portfolio — throwing here keeps it out of the "no positions yet"
      // empty state so it surfaces distinctly instead of being hidden.
      if (!res.ok) throw new Error(`portfolio exposure request failed (${res.status})`);
      return res.json() as Promise<PortfolioExposureResponse>;
    },
    retry: 1,
  });

  const topRanked = exposure?.ranked?.[0] ?? null;
  const headlineScore = exposure?.portfolio_exposure_score ?? topRanked?.portfolio_exposure_score ?? null;
  const headlineStock = exposure?.stock ?? topRanked?.stock ?? null;
  const hasPositions = Boolean(exposure?.assets?.length || exposure?.ranked?.length || exposure?.stocks_covered);

  const liveScore = exposure?.live_portfolio_exposure_score ?? null;
  const liveStatus = exposure?.stock
    ? exposure?.live_status
    : (exposure?.live_stocks_covered ?? 0) > 0
      ? "ready"
      : "collecting_data";

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-heading text-3xl font-bold text-text">Portfolio Exposure</h1>
        {entitlements && (
          <span className="rounded-full border border-violet/40 bg-violet/10 px-3 py-1 font-mono text-xs uppercase tracking-widest text-violet-light">
            {TIER_LABELS[entitlements.tier] ?? entitlements.tier} · ${entitlements.cumulative_usd.toFixed(2)}
          </span>
        )}
      </div>

      <RefreshWalletAssetsControl
        onRefreshed={() => queryClient.invalidateQueries({ queryKey: ["portfolio-exposure"] })}
      />

      {stocks.length > 0 && (
        <div className="mb-4">
          <label htmlFor="portfolio-stock" className="mb-1.5 block font-mono text-xs uppercase tracking-widest text-muted">
            View exposure for
          </label>
          <select
            id="portfolio-stock"
            value={selectedStock}
            onChange={(e) => setSelectedStock(e.target.value)}
            className="w-full max-w-xs rounded-xl border border-white/[0.09] bg-panel2 px-3 py-2 font-mono text-sm text-text focus:border-violet focus:outline-none sm:w-auto"
          >
            <option value="">All stocks (ranked)</option>
            {stocks.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.symbol} — {s.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="rounded-2xl border border-white/[0.09] bg-panel p-6">
        {isLoading ? (
          <>
            <div className="h-3 w-40 animate-pulse rounded bg-panel2" />
            <div className="mt-3 h-9 w-24 animate-pulse rounded bg-panel2" />
            <div className="mt-3 h-3 w-full max-w-md animate-pulse rounded bg-panel2" />
          </>
        ) : (
          <>
            <p className="font-mono text-xs uppercase tracking-widest text-muted">
              {headlineStock ? `Synthetic Exposure — ${headlineStock}` : "Synthetic Exposure Score"}
            </p>
            <p className="mt-2 font-heading text-4xl font-bold text-text">
              {headlineScore != null ? formatScore(headlineScore) : "—"}
            </p>
            <p className={`mt-3 max-w-md font-mono text-xs ${exposureError ? "text-red-400" : "text-muted"}`}>
              {exposureError
                ? "Couldn't load portfolio exposure — try again shortly."
                : (exposure?.note ??
                  (hasPositions
                    ? "Signed correlation between your wallet's crypto holdings and the listed stock, weighted by portfolio share."
                    : "No wallet positions found yet — refresh your wallet to read current on-chain holdings."))}
            </p>
            {!showDetailed && exposure?.stocks_covered != null && exposure.stocks_covered > 0 && (
              <p className="mt-2 font-mono text-[11px] text-muted/70">
                Averaged across {exposure.stocks_covered} stock{exposure.stocks_covered === 1 ? "" : "s"} with exposure data.
              </p>
            )}
            {!exposureError && (
              <div className="mt-3 flex items-center gap-2 border-t border-white/[0.06] pt-3">
                <span className="font-mono text-[10px] uppercase tracking-widest text-muted/60">Live (30-min)</span>
                {liveStatus === "ready" && liveScore != null ? (
                  <span className={`font-mono text-sm font-bold ${liveScore >= 0 ? "text-green" : "text-red-400"}`}>
                    {formatScore(liveScore)}
                  </span>
                ) : liveStatus === "collecting_data" ? (
                  <span className="font-mono text-xs text-muted">Collecting data</span>
                ) : (
                  <span className="font-mono text-xs text-muted">Not available yet</span>
                )}
              </div>
            )}
            {(exposure?.positions_stale || exposure?.quotes_stale) && (
              <p className="mt-2 font-mono text-[11px] text-amber">
                {exposure.positions_stale ? "Wallet positions may be stale — refresh wallet assets. " : ""}
                {exposure.quotes_stale ? "Prices may be stale." : ""}
              </p>
            )}
            {exposure?.total_usd_value != null && exposure.total_usd_value > 0 && (
              <>
                <p className="mt-1 font-mono text-[11px] text-muted/60">
                  Based on {exposure.supported_position_count ?? 0} supported position
                  {(exposure.supported_position_count ?? 0) === 1 ? "" : "s"} · ${exposure.total_usd_value.toFixed(2)} valued
                  {exposure.excluded_position_count ? ` · ${exposure.excluded_position_count} excluded` : ""}
                </p>
                {/* Direct / synthetic / cash allocation — every tier, per-holding
                    breakdowns stay detailed-tier-only further down. */}
                <div className="mt-4 grid grid-cols-3 gap-3 border-t border-white/[0.06] pt-4">
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-muted/60">Direct</p>
                    <p className="mt-1 font-mono text-sm font-bold text-violet-light">
                      {exposure.direct_exposure_pct != null ? `${(exposure.direct_exposure_pct * 100).toFixed(1)}%` : "—"}
                    </p>
                    {exposure.direct_exposure_usd != null && (
                      <p className="font-mono text-[10px] text-muted/50">${exposure.direct_exposure_usd.toFixed(2)}</p>
                    )}
                  </div>
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-muted/60">Synthetic</p>
                    <p className="mt-1 font-mono text-sm font-bold text-text">
                      {exposure.direct_exposure_pct != null && exposure.cash_pct != null
                        ? `${(Math.max(0, 1 - exposure.direct_exposure_pct - exposure.cash_pct) * 100).toFixed(1)}%`
                        : "—"}
                    </p>
                    <p className="font-mono text-[10px] text-muted/50">crypto correlation</p>
                  </div>
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-widest text-muted/60">Cash</p>
                    <p className="mt-1 font-mono text-sm font-bold text-green">
                      {exposure.cash_pct != null ? `${(exposure.cash_pct * 100).toFixed(1)}%` : "—"}
                    </p>
                    {exposure.cash_usd != null && (
                      <p className="font-mono text-[10px] text-muted/50">${exposure.cash_usd.toFixed(2)}</p>
                    )}
                  </div>
                </div>
              </>
            )}
          </>
        )}
      </div>

      {showDetailed && (exposure?.direct_holdings?.length || exposure?.cash_holdings?.length) ? (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {exposure?.direct_holdings && exposure.direct_holdings.length > 0 && (
            <div className="rounded-2xl border border-white/[0.09] bg-panel p-6">
              <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">Stock Token Holdings</p>
              <ul className="space-y-2">
                {exposure.direct_holdings.map((h) => (
                  <li key={h.symbol} className="flex items-center justify-between font-mono text-sm">
                    <span className="text-text">{h.symbol}</span>
                    <span className="text-violet-light">${h.usd_value.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 font-mono text-[10px] text-muted/60">
                Direct exposure — literal ownership, not correlation-based.
              </p>
            </div>
          )}
          {exposure?.cash_holdings && exposure.cash_holdings.length > 0 && (
            <div className="rounded-2xl border border-white/[0.09] bg-panel p-6">
              <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">Cash (Stablecoins)</p>
              <ul className="space-y-2">
                {exposure.cash_holdings.map((h) => (
                  <li key={h.symbol} className="flex items-center justify-between font-mono text-sm">
                    <span className="text-text">{h.symbol}</span>
                    <span className="text-green">${h.usd_value.toFixed(2)}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 font-mono text-[10px] text-muted/60">
                Zero correlation — counted in total value only.
              </p>
            </div>
          )}
        </div>
      ) : null}

      {showDetailed && (
        <div className="mt-4 rounded-2xl border border-white/[0.09] bg-panel p-6">
          <p className="mb-3 font-mono text-xs uppercase tracking-widest text-muted">Synthetic Holdings Weight</p>
          {exposure?.assets?.length ? (
            <ul className="space-y-2">
              {exposure.assets.map((a) => (
                <li key={a.symbol} className="flex items-center justify-between font-mono text-sm">
                  <span className="text-text">{a.symbol}</span>
                  <span className="text-muted">{(a.weight * 100).toFixed(1)}%</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="font-mono text-sm text-muted/70">
              Detailed asset and sector exposure will appear here once wallet positions are refreshed.
            </p>
          )}
          {exposure?.category_exposure && exposure.category_exposure.length > 0 && (
            <>
              <p className="mb-2 mt-5 font-mono text-xs uppercase tracking-widest text-muted">Sector Exposure</p>
              <ul className="space-y-1.5">
                {exposure.category_exposure.map((c) => (
                  <li key={c.category} className="flex items-center justify-between font-mono text-sm">
                    <span className="text-text">{c.category}</span>
                    <span className="text-muted">{(c.weight * 100).toFixed(1)}%</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {exposure?.ranked && exposure.ranked.length > 1 && (
            <>
              <p className="mb-2 mt-5 font-mono text-xs uppercase tracking-widest text-muted">Ranked by Stock</p>
              <ul className="space-y-1.5">
                {exposure.ranked.slice(0, 5).map((r) => (
                  <li key={r.stock} className="flex items-center justify-between font-mono text-sm">
                    <span className="text-text">{r.stock}</span>
                    <span className={r.portfolio_exposure_score >= 0 ? "text-green" : "text-red-400"}>
                      {formatScore(r.portfolio_exposure_score)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {showComingSoon && (
        <div className="mt-4 flex flex-wrap gap-2">
          {(exposure?.coming_soon ?? ["advanced_graphs", "longer_portfolio_history", "alerts"]).map((f) => (
            <span
              key={f}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.09] bg-panel2 px-3 py-1 font-mono text-xs text-muted"
            >
              {COMING_SOON_LABELS[f] ?? f} · <span className="text-violet-light">Coming Soon</span>
            </span>
          ))}
        </div>
      )}

      <div className="mt-4">
        <PurchaseVerificationForm />
      </div>

      <Link href="/" className="mt-6 inline-block font-mono text-xs text-muted/60 underline-offset-4 hover:text-muted hover:underline">
        ← Back to home
      </Link>
    </div>
  );
}
