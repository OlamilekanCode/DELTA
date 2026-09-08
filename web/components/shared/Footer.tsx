import Link from "next/link";
import BrandLogo from "@/components/shared/BrandLogo";

const navLinks = [
  { href: "/explore",     label: "Explore" },
  { href: "/methodology", label: "Methodology" },
];

const legalLinks = [
  { href: "/terms",           label: "Terms" },
  { href: "/privacy",         label: "Privacy" },
  { href: "/risk-disclosure", label: "Risk Disclosure" },
];

export default function Footer() {
  return (
    <footer className="border-t border-white/[0.09] bg-panel mt-24">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <BrandLogo size={22} />
              <span className="font-heading text-xl font-bold text-violet">Synthetic Exposure</span>
            </div>
            <p className="mt-2 max-w-xs text-sm text-muted">
              Map how stocks and crypto move together.
            </p>
            <div className="mt-4 flex items-center gap-2">
              <a
                href="https://x.com/SyntheticExposure"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Follow on X"
                className="flex size-8 items-center justify-center rounded-lg border border-white/[0.09] bg-panel2 text-muted transition-colors hover:border-violet/40 hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
              >
                <svg className="size-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.742l7.727-8.854L1.254 2.25H8.08l4.259 5.632L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z" />
                </svg>
              </a>
              <a
                href="https://discord.gg/SyntheticExposure"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Join Discord"
                className="flex size-8 items-center justify-center rounded-lg border border-white/[0.09] bg-panel2 text-muted transition-colors hover:border-violet/40 hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
              >
                <svg className="size-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.003.022.015.043.033.054a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
                </svg>
              </a>
            </div>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:gap-8 lg:gap-12">
            <div>
              <p className="mb-3 text-xs font-medium uppercase tracking-widest text-muted">Product</p>
              <ul className="space-y-2">
                {navLinks.map((l) => (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className="text-sm text-muted transition-colors hover:text-text focus-visible:text-text"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="mb-3 text-xs font-medium uppercase tracking-widest text-muted">Legal</p>
              <ul className="space-y-2">
                {legalLinks.map((l) => (
                  <li key={l.href}>
                    <Link
                      href={l.href}
                      className="text-sm text-muted transition-colors hover:text-text focus-visible:text-text"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* $SynthEx token strip */}
        <div className="mt-8 rounded-xl border border-violet/[0.15] bg-violet/[0.04] px-4 py-3 sm:mt-12">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-mono text-xs font-bold text-violet-light">$SynthEx</span>
            <span className="text-white/20">·</span>
            <span className="font-mono text-xs text-muted">Main Access Token</span>
            <span className="text-white/20">·</span>
            <span className="font-mono text-xs text-muted">Hold $SynthEx to unlock premium analytics &amp; portfolio exposure</span>
          </div>
        </div>

        <div className="mt-5 border-t border-white/[0.09] pt-5">
          <p className="text-xs text-muted">
            © 2026 Synthetic Exposure. Not investment advice. Exposure Scores reflect historical correlation only.
          </p>
        </div>
      </div>
    </footer>
  );
}
