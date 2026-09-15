/**
 * Maps raw wallet/SIWE failures to short, plain-English messages for the
 * sign-in UI. Never surface a raw error string here — a wallet's own
 * rejection message, a viem/wagmi error, or a backend SiweError code (see
 * api/app/services/auth.py's SiweError) all read as debug output to a user,
 * not an explanation of what to do next.
 */

/** Backend SiweError codes (api/app/services/auth.py), grouped by the
 * action a user can actually take in response. */
const SIWE_CODE_MESSAGES: Record<string, string> = {
  // The sign-in request itself expired or was already used — just retry.
  invalid_nonce: "Your sign-in request expired. Please try again.",
  nonce_expired: "Your sign-in request expired. Please try again.",
  nonce_reused: "Your sign-in request expired. Please try again.",
  message_expired: "Your sign-in request expired. Please try again.",
  issued_in_future: "Your sign-in request expired. Please try again. If the problem continues, check your device's clock is correct.",

  // Wallet connected to the wrong network.
  chain_mismatch: "Your wallet is on the wrong network. Switch to the correct network and try again.",
  malformed_chain_id: "Your wallet is on the wrong network. Switch to the correct network and try again.",

  // The signature didn't check out.
  invalid_signature: "We couldn't verify your signature. Please try signing in again.",
  signature_address_mismatch: "We couldn't verify your signature. Please try signing in again.",
  signature_too_long: "We couldn't verify your signature. Please try signing in again.",

  // Request didn't match this site — possible stale tab or misconfiguration.
  domain_mismatch: "This sign-in request doesn't match this site. Please refresh the page and try again.",
  uri_mismatch: "This sign-in request doesn't match this site. Please refresh the page and try again.",
  uri_scheme_invalid: "This sign-in request doesn't match this site. Please refresh the page and try again.",
  uri_host_invalid: "This sign-in request doesn't match this site. Please refresh the page and try again.",
};

/** Everything else from SiweError (malformed_message, malformed_address,
 * malformed_timestamp, unsupported_version, message_too_long, any dynamic
 * missing-field or duplicate-field code) is an internal message-building
 * bug, not something the user caused — no per-code message is worth
 * showing them, just a generic retry prompt. */
const GENERIC_SIGN_IN_FAILED = "Sign-in failed. Please try again.";

function siweCodeMessage(code: string): string {
  return SIWE_CODE_MESSAGES[code] ?? GENERIC_SIGN_IN_FAILED;
}

/** The verify_siwe_message service is out entirely (RPC/chain not
 * configured server-side) — not the user's fault and retrying won't help
 * immediately. */
const CHAIN_NOT_CONFIGURED_MESSAGE = "Wallet sign-in isn't available right now. Please try again in a few minutes.";
const RATE_LIMITED_MESSAGE = "Too many sign-in attempts. Please wait a moment and try again.";
const NONCE_FETCH_FAILED_MESSAGE = "Couldn't start sign-in. Check your connection and try again.";

/** Turns the HTTP response from POST /api/auth/verify (proxied straight
 * through from the FastAPI backend, so its body is {"detail": "..."} — a
 * SiweError code, "chain_not_configured", or "rate_limited") into a
 * user-facing message. */
export async function verifyErrorMessage(res: Response): Promise<string> {
  if (res.status === 429) return RATE_LIMITED_MESSAGE;
  if (res.status === 503) return CHAIN_NOT_CONFIGURED_MESSAGE;
  const body = await res.json().catch(() => null);
  const code = typeof body?.detail === "string" ? body.detail : null;
  if (code === "chain_not_configured") return CHAIN_NOT_CONFIGURED_MESSAGE;
  if (code === "rate_limited") return RATE_LIMITED_MESSAGE;
  return code ? siweCodeMessage(code) : GENERIC_SIGN_IN_FAILED;
}

export function nonceFetchErrorMessage(): string {
  return NONCE_FETCH_FAILED_MESSAGE;
}

/** Wallet-side failures from wagmi's signMessageAsync — viem's provider
 * errors (see node_modules/viem/_esm/errors/rpc.js) carry a stable `.name`
 * regardless of which wallet (MetaMask/WalletConnect/Coinbase/etc.)
 * produced them; a raw `.message` is often multi-line viem debug output
 * ("Docs: ...", "Version: ...") that must never reach the UI. */
export function signatureErrorMessage(err: unknown): string {
  const name = (err as { name?: unknown } | null)?.name;
  const code = (err as { code?: unknown } | null)?.code;
  if (name === "UserRejectedRequestError" || code === 4001) {
    return "You declined the signature request. To sign in, approve the signature in your wallet.";
  }
  if (name === "ChainDisconnectedError" || name === "ProviderDisconnectedError") {
    return "Your wallet disconnected. Please reconnect and try again.";
  }
  return "Your wallet couldn't sign the message. Please try again.";
}
