"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import ConnectWalletButton from "@/components/wallet/ConnectWalletButton";
import BrandLogo from "@/components/shared/BrandLogo";
import MarketStatusBadge from "@/components/market/MarketStatusBadge";

const navLinks: { href: string; label: string }[] = [
  { href: "/explore",     label: "Explore" },
  { href: "/graph/NVDA",  label: "Exposure Graph" },
  { href: "/portfolio",   label: "Portfolio" },
  { href: "/methodology", label: "Methodology" },
];

export default function Navigation() {
  const [scrolled, setScrolled]   = useState(false);
  const [menuOpen, setMenuOpen]   = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") closeMenu(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menuOpen, closeMenu]);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  return (
    <>
      <header
        role="banner"
        className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
          scrolled
            ? "border-b border-white/[0.09] bg-bg/90 backdrop-blur-md"
            : "bg-transparent"
        }`}
      >
        <nav
          role="navigation"
          aria-label="Main navigation"
          className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
        >
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 font-heading text-2xl font-bold text-violet transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
            aria-label="Synthetic Exposure home"
          >
            <BrandLogo size={24} />
            Synthetic Exposure
          </Link>

          {/* Desktop links */}
          <ul className="hidden items-center gap-8 md:flex" role="list">
            {navLinks.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="text-sm font-medium text-muted transition-colors hover:text-text focus-visible:text-text"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-3">
            {/* Social icons */}
            <a
              href="https://x.com/SyntheticExposure"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Follow on X"
              className="flex size-8 items-center justify-center rounded-lg text-muted transition-colors hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
            >
              <svg className="size-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.742l7.727-8.854L1.254 2.25H8.08l4.259 5.632L18.244 2.25zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77z" />
              </svg>
            </a>
            <a
              href="https://discord.gg/SyntheticExposure"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Join Discord"
              className="flex size-8 items-center justify-center rounded-lg text-muted transition-colors hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
            >
              <svg className="size-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.003.022.015.043.033.054a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" />
              </svg>
            </a>

            <MarketStatusBadge className="hidden lg:inline-flex" />
            <ConnectWalletButton className="hidden md:inline-flex" />

            {/* Mobile hamburger */}
            <button
              type="button"
              aria-label={menuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={menuOpen}
              aria-controls="mobile-menu"
              className="inline-flex size-10 items-center justify-center rounded-lg border border-white/[0.09] bg-panel text-muted transition-colors hover:text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet md:hidden"
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? (
                <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
              )}
            </button>
          </div>
        </nav>
      </header>

      {/* Mobile drawer */}
      {menuOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
          id="mobile-menu"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-bg/80 backdrop-blur-sm"
            onClick={closeMenu}
            aria-hidden="true"
          />

          {/* Drawer panel */}
          <div className="absolute inset-x-0 top-0 flex flex-col bg-panel pt-16 pb-8 px-4 shadow-2xl sm:pt-20 sm:px-6">
            <ul className="space-y-1" role="list">
              {navLinks.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    onClick={closeMenu}
                    className="flex w-full items-center rounded-lg px-4 py-3 text-base font-medium text-muted transition-colors hover:bg-panel2 hover:text-text focus-visible:bg-panel2 focus-visible:text-text focus-visible:outline-none"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
            <div className="mt-6 border-t border-white/[0.09] pt-6">
              <ConnectWalletButton className="w-full justify-center" />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
