"use client";

import { createAppKit } from "@reown/appkit/react";
import { WagmiAdapter } from "@reown/appkit-adapter-wagmi";
import { base } from "@reown/appkit/networks";
import type { AppKitNetwork } from "@reown/appkit/networks";
import { defineChain } from "viem";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";
import { useState } from "react";
import type React from "react";
import { getConfiguredChainId, isWalletFullyConfigured } from "@/lib/wallet-config";

const PROJECT_ID = process.env.NEXT_PUBLIC_REOWN_PROJECT_ID ?? "";

/**
 * Builds the Robinhood Chain network definition from environment variables —
 * never a hardcoded chain ID. Returns null (chain not configured) unless the
 * Reown project ID, the chain ID AND its public RPC URL are ALL present —
 * see lib/wallet-config.ts for why these three must be checked together.
 *
 * NEXT_PUBLIC_SYNTHEX_RPC_URL is a separate, explicitly public RPC endpoint
 * for wallet-facing reads/chain-add prompts only — never the private
 * server-only ROBINHOOD_RPC_URL, which never reaches the frontend.
 */
function buildRobinhoodChainNetwork(): AppKitNetwork | null {
  if (!isWalletFullyConfigured()) return null;
  const chainId = getConfiguredChainId();
  const rpcUrl = process.env.NEXT_PUBLIC_SYNTHEX_RPC_URL;
  if (chainId === null || !rpcUrl) return null;

  return defineChain({
    id: chainId,
    name: "Robinhood Chain",
    nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
    rpcUrls: { default: { http: [rpcUrl] } },
  }) as AppKitNetwork;
}

const robinhoodChain = buildRobinhoodChainNetwork();

// AppKit requires at least one network at init time. Base is only ever a
// bootstrap placeholder here — WalletStateManager compares the wallet's
// connected chain ID against NEXT_PUBLIC_SYNTHEX_CHAIN_ID for access
// decisions and shows "wrong chain" / "config unavailable" accordingly, so
// a Base connection is never silently treated as "the correct chain".
const networks: [AppKitNetwork, ...AppKitNetwork[]] = robinhoodChain
  ? [robinhoodChain, base]
  : [base];

const wagmiAdapter = new WagmiAdapter({ projectId: PROJECT_ID, networks, ssr: true });

createAppKit({
  adapters: [wagmiAdapter],
  projectId: PROJECT_ID,
  networks,
  defaultNetwork: networks[0],
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
