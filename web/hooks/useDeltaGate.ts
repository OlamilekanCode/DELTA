"use client";

import { useEffect, useState } from "react";
import { useAccount, useConfig } from "wagmi";
import { hasDeltaAccess } from "@/lib/delta-gate";

export function useDeltaGate() {
  const { address, isConnected } = useAccount();
  const config = useConfig();
  const [_hasAccess, setHasAccess] = useState(false);

  useEffect(() => {
    if (!isConnected || !address) return;

    let cancelled = false;
    hasDeltaAccess(config, address).then((result) => {
      if (!cancelled) setHasAccess(result);
    });
    return () => { cancelled = true; };
  }, [address, isConnected, config]);

  return {
    hasAccess: isConnected ? _hasAccess : false,
    isConnected,
  };
}
