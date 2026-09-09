"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

interface SessionResponse {
  wallet_address: string | null;
  authenticated: boolean;
}

const SESSION_QUERY_KEY = ["session"];

async function fetchSession(): Promise<SessionResponse> {
  const res = await fetch("/api/auth/session", { cache: "no-store" });
  if (!res.ok) return { wallet_address: null, authenticated: false };
  return res.json();
}

export function useSession() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: SESSION_QUERY_KEY,
    queryFn: fetchSession,
  });

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: SESSION_QUERY_KEY });
  }, [queryClient]);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    queryClient.setQueryData<SessionResponse>(SESSION_QUERY_KEY, {
      wallet_address: null,
      authenticated: false,
    });
  }, [queryClient]);

  return {
    walletAddress: data?.wallet_address ?? null,
    authenticated: Boolean(data?.authenticated),
    loading: isLoading,
    refresh,
    logout,
  };
}
