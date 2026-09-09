import type { NextConfig } from "next";
import BundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = BundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

// Anti-clickjacking + a baseline CSP. A wallet-signing, session-cookie app
// must never be embeddable in another site's iframe (frame-ancestors
// 'none' below, plus X-Frame-Options for older browsers) — that's the one
// non-negotiable directive here.
//
// connect-src/img-src/frame-src are deliberately permissive (https:/wss:)
// rather than an exact allowlist: Reown AppKit/WalletConnect connects to
// its relay servers and to whichever wallet the user has, and to remote
// wallet-icon CDNs, none of which are practical to enumerate exhaustively
// without live-testing every supported wallet's connect flow. script-src
// and style-src keep 'unsafe-inline' for the same reason — this codebase
// uses React inline `style={{}}` extensively (inline style ATTRIBUTES are
// governed by style-src, not just <style> tags), and locking either down
// without nonce-based CSP infrastructure risks silently breaking
// hydration or every dynamically-colored component with no visible error.
// Tightening either is real follow-up work, not something to guess at
// without a real browser + real wallet-connect flow to verify against.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https:",
  "font-src 'self' data:",
  "connect-src 'self' https: wss:",
  "frame-src 'self' https:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  agentRules: false,
  turbopack: {
    root: __dirname,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Content-Security-Policy", value: CSP },
        ],
      },
    ];
  },
};

export default withBundleAnalyzer(nextConfig);
