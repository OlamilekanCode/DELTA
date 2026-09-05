import { readContract } from "@wagmi/core";
import { erc20Abi } from "viem";

const TOKEN_ADDRESS = process.env.NEXT_PUBLIC_DELTA_TOKEN_ADDRESS as `0x${string}` | undefined;
const MIN_BALANCE_RAW = process.env.NEXT_PUBLIC_DELTA_MIN_BALANCE ?? "";

const ZERO = BigInt(0);

function getMinBalance(): bigint {
  try {
    return MIN_BALANCE_RAW ? BigInt(MIN_BALANCE_RAW) : ZERO;
  } catch {
    return ZERO;
  }
}

// Returns false when gating is not configured (env vars empty) — no-op
export async function hasDeltaAccess(
  wagmiConfig: Parameters<typeof readContract>[0],
  address: `0x${string}`
): Promise<boolean> {
  const minBalance = getMinBalance();
  if (!TOKEN_ADDRESS || minBalance === ZERO) return false;

  try {
    const balance = await readContract(wagmiConfig, {
      address: TOKEN_ADDRESS,
      abi: erc20Abi,
      functionName: "balanceOf",
      args: [address],
    });
    return (balance as bigint) >= minBalance;
  } catch {
    return false;
  }
}
