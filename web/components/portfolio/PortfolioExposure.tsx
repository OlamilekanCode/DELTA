"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSwitchChain } from "wagmi";
import { useWalletState } from "@/components/wallet/WalletStateManager";
import ConnectWalletButton from "@/components/wallet/ConnectWalletButton";
import { formatScore } from "@/lib/format";

const DEX_URL = process.env.NEXT_PUBLIC_SYNTHEX_BUY_URL ?? "";
const TIER_LABELS: Record<string, string> = {
  summary: "Summary", detailed: "Detailed", premium: "Premium",
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

export default function PortfolioExposure() {
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
        </Shell>
      );

    case "tier_summary":
    case "tier_detailed":
    case "tier_premium":
      return <PortfolioDetail tier={state} entitlements={entitlements} />;

    default:
      return null;
  }
}

function PortfolioDetail({
  tier,
  entitlements,
}: {
  tier: "tier_summary" | "tier_detailed" | "tier_premium";
  entitlements: { tier: string; cumulative_usd: number } | null;
}) {
  const showDetailed = tier === "tier_detailed" || tier === "tier_premium";
  const showComingSoon = tier === "tier_premium";
  const { data: exposure } = useQuery({
    queryKey: ["portfolio-exposure"],
    queryFn: async () => {
      const res = await fetch("/api/portfolio/exposure", { cache: "no-store" });
      if (!res.ok) return null;
      return res.json() as Promise<{ portfolio_exposure_score: number | null; note?: string }>;
    },
  });

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

      <div className="rounded-2xl border border-white/[0.09] bg-panel p-6">
        <p className="font-mono text-xs uppercase tracking-widest text-muted">Portfolio Exposure Score</p>
        <p className="mt-2 font-heading text-4xl font-bold text-text">
          {exposure?.portfolio_exposure_score != null ? formatScore(exposure.portfolio_exposure_score) : "—"}
        </p>
        <p className="mt-3 max-w-md font-mono text-xs text-muted">
          {exposure?.note ??
            "Portfolio position tracking is not yet available — this will populate once wallet asset positions can be read and weighted against each asset's signed Exposure Score."}
        </p>
      </div>

      {showDetailed && (
        <div className="mt-4 rounded-2xl border border-white/[0.09] bg-panel p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Per-Asset Breakdown</p>
          <p className="mt-2 font-mono text-sm text-muted/70">
            Detailed asset and sector exposure will appear here once position tracking is live.
          </p>
        </div>
      )}

      {showComingSoon && (
        <div className="mt-4 flex flex-wrap gap-2">
          {["Advanced graphs", "Longer portfolio history", "Alerts"].map((f) => (
            <span
              key={f}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.09] bg-panel2 px-3 py-1 font-mono text-xs text-muted"
            >
              {f} · <span className="text-violet-light">Coming Soon</span>
            </span>
          ))}
        </div>
      )}

      <Link href="/" className="mt-6 inline-block font-mono text-xs text-muted/60 underline-offset-4 hover:text-muted hover:underline">
        ← Back to home
      </Link>
    </div>
  );
}
