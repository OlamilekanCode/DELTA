"use client";

import { createAppKit } from "@reown/appkit/react";
import { WagmiAdapter } from "@reown/appkit-adapter-wagmi";
// TODO: replace `base` with Robinhood Chain once its chain ID, a public RPC
// URL and contract addresses are supplied — none of which exist yet and none
// may be invented. Base (8453) is a temporary SDK-init placeholder only; it
// must never be treated as "the correct chain" for access decisions. Actual
// chain-correctness gating happens in WalletStateManager, which compares the
// wallet's connected chain ID against NEXT_PUBLIC_SYNTHEX_CHAIN_ID and shows
// "wrong chain" / "config unavailable" states accordingly — connecting to
// this placeholder network is never treated as success.
import { base } from "@reown/appkit/networks";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";
import { useState } from "react";
import type React from "react";

const PROJECT_ID = process.env.NEXT_PUBLIC_REOWN_PROJECT_ID ?? "";

// Initialise at module scope so every hook (useAppKit, useAccount, etc.)
// can find the context regardless of when the component tree renders.
const wagmiAdapter = new WagmiAdapter({ projectId: PROJECT_ID, networks: [base], ssr: true });

createAppKit({
  adapters: [wagmiAdapter],
  projectId: PROJECT_ID,
  networks: [base],
  defaultNetwork: base,
  metadata: {
    name: "Synthetic Exposure",
    description: "Map the Market. Stock ↔ Crypto Exposure.",
    url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
    icons: [],
  },
  features: { analytics: false },
});

export default function Web3Provider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={wagmiAdapter.wagmiConfig}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </WagmiProvider>
  );
}
