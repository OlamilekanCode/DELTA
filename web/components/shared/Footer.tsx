import Link from "next/link";

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
      <div className="mx-auto max-w-7xl px-6 py-12 lg:px-8">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div>
            <span className="font-heading text-xl font-bold text-violet">DELTA</span>
            <p className="mt-2 max-w-xs text-sm text-muted">
              Map how stocks and crypto move together using historical market data.
            </p>
          </div>

          <div className="flex flex-col gap-6 sm:flex-row sm:gap-12">
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

        <div className="mt-12 border-t border-white/[0.09] pt-8">
          <p className="text-xs text-muted">
            © 2026 DELTA. Not investment advice. Exposure Scores reflect historical correlation only.
          </p>
        </div>
      </div>
    </footer>
  );
}
