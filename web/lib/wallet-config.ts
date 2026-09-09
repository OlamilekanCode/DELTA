/**
 * Wallet/chain configuration is only usable when the Reown project ID, the
 * Robinhood Chain ID and its public RPC URL are ALL present. Any one of the
 * three missing means wallet connection or chain-switching cannot actually
 * work — a chain ID configured with no RPC URL (or either with no Reown
 * project ID) previously let Web3Provider silently fall back to Base while
 * WalletStateManager still believed the chain was configured, producing an
 * unrecoverable "wrong chain" state with no way to actually switch. Both
 * must check the same three variables together.
 */

export function getConfiguredChainId(): number | null {
  const raw = process.env.NEXT_PUBLIC_SYNTHEX_CHAIN_ID;
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export function isWalletFullyConfigured(): boolean {
  const chainId = getConfiguredChainId();
  const rpcUrl = process.env.NEXT_PUBLIC_SYNTHEX_RPC_URL;
  const projectId = process.env.NEXT_PUBLIC_REOWN_PROJECT_ID;
  return chainId !== null && Boolean(rpcUrl) && Boolean(projectId);
}
