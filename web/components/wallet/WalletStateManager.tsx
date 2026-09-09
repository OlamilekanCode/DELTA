"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type React from "react";
import { useQuery } from "@tanstack/react-query";
import { useAccount, useSignMessage } from "wagmi";
import { useSession } from "@/hooks/useSession";
import { getConfiguredChainId, isWalletFullyConfigured } from "@/lib/wallet-config";

/**
 * The 10 required wallet states, covering disconnected/wrong-chain/unauthenticated
 * through each verified purchase tier.
 * `loading` is an 11th transitional state while entitlements are being
 * resolved after authentication — never shown for more than a beat.
 */
export type WalletState =
  | "disconnected"
  | "config_unavailable"
  | "wrong_chain"
  | "unauthenticated"
  | "loading"
  | "no_token"
  | "insufficient_balance"
  | "holder_locked"
  | "tier_summary"
  | "tier_detailed"
  | "tier_premium";

export type PortfolioTier = "locked" | "summary" | "detailed" | "premium";

interface EntitlementsStatus {
  tier: PortfolioTier;
  cumulative_usd: number;
  is_holder: boolean;
  synthex_balance: string | null;
  synthex_balance_checked_at: string | null;
}

interface WalletStateContextValue {
  state: WalletState;
  address: string | null;
  chainConfigured: boolean;
  configuredChainId: number | null;
  connectedChainId: number | null;
  entitlements: EntitlementsStatus | null;
  signInError: string | null;
  signingIn: boolean;
  signIn: () => Promise<void>;
  logout: () => Promise<void>;
}

const WalletStateContext = createContext<WalletStateContextValue | null>(null);

export function useWalletState(): WalletStateContextValue {
  const ctx = useContext(WalletStateContext);
  if (!ctx) throw new Error("useWalletState must be used within WalletStateManager");
  return ctx;
}

async function fetchEntitlements(): Promise<EntitlementsStatus | null> {
  const res = await fetch("/api/entitlements/status", { cache: "no-store" });
  if (!res.ok) return null;
  return res.json();
}

/**
 * Triggers a fresh on-chain balance read (rate-limited server-side to a
 * ~5-minute cache window — see api/app/services/holder.py) and returns the
 * updated status in one round trip.
 */
async function refreshEntitlements(): Promise<EntitlementsStatus | null> {
  await fetch("/api/entitlements/refresh", { method: "POST" }).catch(() => {});
  return fetchEntitlements();
}

async function buildSiweMessage(address: string, chainId: number, nonce: string): Promise<string> {
  const domain = window.location.host;
  const uri = window.location.origin;
  const issuedAt = new Date();
  const expiration = new Date(issuedAt.getTime() + 10 * 60 * 1000);
  return [
    `${domain} wants you to sign in with your Ethereum account:`,
    address,
    "",
    "Sign in to Synthetic Exposure.",
    "",
    `URI: ${uri}`,
    "Version: 1",
    `Chain ID: ${chainId}`,
    `Nonce: ${nonce}`,
    `Issued At: ${issuedAt.toISOString()}`,
    `Expiration Time: ${expiration.toISOString()}`,
  ].join("\n");
}

export default function WalletStateManager({ children }: { children: React.ReactNode }) {
  const { address, isConnected, chainId } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const session = useSession();

  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);

  const configuredChainId = useMemo(() => getConfiguredChainId(), []);
  // Requires the Reown project ID and public RPC URL too, not just the
  // chain ID — Web3Provider only actually registers the chain (so the
  // wallet can ever switch to it) when all three are present.
  const chainConfigured = useMemo(() => isWalletFullyConfigured(), []);

  // Forces a fresh on-chain balance read (server-side rate-limited) after
  // login and every 5 minutes while authenticated and the tab is visible —
  // never on every route change or ordinary asset-page request.
  const { data: entitlements = null, isLoading: entitlementsLoading } = useQuery({
    queryKey: ["entitlements-status"],
    queryFn: refreshEntitlements,
    enabled: session.authenticated,
    refetchInterval: session.authenticated ? 5 * 60_000 : false,
    refetchIntervalInBackground: false,
  });

  // Switching the connected wallet address ends the active session — each
  // address is a separate account and must re-authenticate.
  useEffect(() => {
    if (session.authenticated && address && session.walletAddress &&
        address.toLowerCase() !== session.walletAddress.toLowerCase()) {
      session.logout();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [address]);

  const signIn = useCallback(async () => {
    if (!address || !configuredChainId) return;
    setSigningIn(true);
    setSignInError(null);
    try {
      const nonceRes = await fetch("/api/auth/nonce", { method: "POST" });
      if (!nonceRes.ok) throw new Error("Could not get a sign-in nonce");
      const { nonce } = await nonceRes.json();

      const message = await buildSiweMessage(address, configuredChainId, nonce);
      const signature = await signMessageAsync({ message });

      const verifyRes = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, signature }),
      });
      if (!verifyRes.ok) {
        const body = await verifyRes.json().catch(() => ({}));
        throw new Error(body.error ?? "Sign-in verification failed");
      }
      await session.refresh();
    } catch (err) {
      setSignInError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setSigningIn(false);
    }
  }, [address, configuredChainId, signMessageAsync, session]);

  const state: WalletState = useMemo(() => {
    if (!isConnected || !address) return "disconnected";
    if (!chainConfigured) return "config_unavailable";
    if (chainId !== configuredChainId) return "wrong_chain";
    if (!session.authenticated) return "unauthenticated";
    if (entitlementsLoading || !entitlements) return "loading";
    if (!entitlements.is_holder) {
      return entitlements.tier === "locked" ? "no_token" : "insufficient_balance";
    }
    switch (entitlements.tier) {
      case "locked": return "holder_locked";
      case "summary": return "tier_summary";
      case "detailed": return "tier_detailed";
      case "premium": return "tier_premium";
      default: return "no_token";
    }
  }, [isConnected, address, chainConfigured, chainId, configuredChainId, session.authenticated, entitlementsLoading, entitlements]);

  const value: WalletStateContextValue = {
    state,
    address: address ?? null,
    chainConfigured,
    configuredChainId,
    connectedChainId: chainId ?? null,
    entitlements,
    signInError,
    signingIn,
    signIn,
    logout: session.logout,
  };

  return <WalletStateContext.Provider value={value}>{children}</WalletStateContext.Provider>;
}
