"use client";

import { useAppKit } from "@reown/appkit/react";
import { useAccount } from "wagmi";

export default function ConnectWalletButton({ className = "" }: { className?: string }) {
  const { open } = useAppKit();
  const { address, isConnected } = useAccount();

  const label = isConnected && address
    ? `${address.slice(0, 6)}…${address.slice(-4)}`
    : "Connect wallet";

  return (
    <button
      type="button"
      onClick={() => open()}
      className={`inline-flex items-center gap-2 rounded-lg border border-violet/60 bg-violet/10 px-4 py-2 text-sm font-medium text-violet-light transition-all hover:border-violet hover:bg-violet/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet active:scale-95 ${className}`}
      aria-label={isConnected ? "Manage wallet" : "Connect wallet"}
    >
      <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 12m18 0v5.25A2.25 2.25 0 0118.75 19.5H5.25A2.25 2.25 0 013 17.25V12m18 0V6.75A2.25 2.25 0 0018.75 4.5H5.25A2.25 2.25 0 003 6.75V12" />
      </svg>
      {label}
    </button>
  );
}
