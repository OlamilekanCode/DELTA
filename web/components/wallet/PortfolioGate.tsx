"use client";

import Link from "next/link";
import { useDeltaGate } from "@/hooks/useDeltaGate";
import ConnectWalletButton from "./ConnectWalletButton";

const DEX_URL = process.env.NEXT_PUBLIC_DEX_BUY_URL ?? "";

export default function PortfolioGate() {
  const { hasAccess, isConnected } = useDeltaGate();

  if (!isConnected) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
        <WalletIcon />
        <h1 className="font-heading text-3xl font-bold text-text sm:text-4xl">
          Portfolio Exposure
        </h1>
        <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
          Connect your wallet to check your $DELTA balance and unlock portfolio exposure analysis.
        </p>
        <ConnectWalletButton className="px-6 py-3 text-base" />
        <Link href="/" className="font-mono text-xs text-muted/60 underline-offset-4 hover:text-muted hover:underline">
          ← Back to home
        </Link>
      </div>
    );
  }

  if (!hasAccess) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
        <TokenIcon />
        <h1 className="font-heading text-3xl font-bold text-text sm:text-4xl">
          $DELTA Required
        </h1>
        <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
          Portfolio exposure analysis is available to $DELTA token holders. Acquire $DELTA to unlock access.
        </p>
        <p className="font-mono text-xs text-muted/50">
          Analytical tool · Not financial advice
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {DEX_URL && (
            <a
              href={DEX_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-xl bg-violet px-6 py-3 text-sm font-bold text-white transition-all hover:bg-violet/90 active:scale-95"
            >
              Get $DELTA
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </a>
          )}
          <Link href="/" className="inline-flex items-center rounded-xl border border-white/20 px-6 py-3 text-sm font-semibold text-text transition-all hover:border-white/40 active:scale-95">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-4 text-center">
      <CheckIcon />
      <h1 className="font-heading text-3xl font-bold text-text sm:text-4xl">
        Portfolio Exposure
      </h1>
      <p className="max-w-sm font-mono text-sm leading-relaxed text-muted">
        Full portfolio analysis is coming soon. Your $DELTA balance has been verified — you&apos;ll be among the first to access it.
      </p>
      <Link href="/#nvda-example" className="font-mono text-sm text-violet-light underline-offset-4 hover:underline">
        Explore the NVDA example →
      </Link>
    </div>
  );
}

function WalletIcon() {
  return (
    <div className="flex size-16 items-center justify-center rounded-2xl bg-violet/10">
      <svg className="size-8 text-violet-light" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 12m18 0v5.25A2.25 2.25 0 0 1 18.75 19.5H5.25A2.25 2.25 0 0 1 3 17.25V12m18 0V6.75A2.25 2.25 0 0 0 18.75 4.5H5.25A2.25 2.25 0 0 0 3 6.75V12" />
      </svg>
    </div>
  );
}

function TokenIcon() {
  return (
    <div className="flex size-16 items-center justify-center rounded-2xl bg-amber/10">
      <svg className="size-8 text-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
      </svg>
    </div>
  );
}

function CheckIcon() {
  return (
    <div className="flex size-16 items-center justify-center rounded-2xl bg-green/10">
      <svg className="size-8 text-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    </div>
  );
}
