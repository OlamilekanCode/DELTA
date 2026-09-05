"use client";

import { createAppKit } from "@reown/appkit/react";
import { WagmiAdapter } from "@reown/appkit-adapter-wagmi";
import { base } from "@reown/appkit/networks";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WagmiProvider } from "wagmi";
import { useState } from "react";
import type React from "react";

const PROJECT_ID = process.env.NEXT_PUBLIC_REOWN_PROJECT_ID ?? "";

// Initialise at module scope so every hook (useAppKit, useAccount, etc.)
// can find the context regardless of when the component tree renders.
const wagmiAdapter = new WagmiAdapter({ projectId: PROJECT_ID, networks: [base] });

createAppKit({
  adapters: [wagmiAdapter],
  projectId: PROJECT_ID,
  networks: [base],
  defaultNetwork: base,
  metadata: {
    name: "DELTA",
    description: "Map the Market. Stock ↔ Crypto Exposure.",
    url: "https://delta.example.com",
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
