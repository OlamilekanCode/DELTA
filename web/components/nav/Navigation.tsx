"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import ConnectWalletButton from "@/components/wallet/ConnectWalletButton";

const navLinks = [
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
          className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-8"
        >
          {/* Logo */}
          <Link
            href="/"
            className="font-heading text-2xl font-bold text-violet transition-opacity hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
            aria-label="DELTA home"
          >
            DELTA
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
          <div className="absolute inset-x-0 top-0 flex flex-col bg-panel pt-20 pb-8 px-6 shadow-2xl">
            <ul className="space-y-1" role="list">
              {navLinks.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    onClick={closeMenu}
                    className="flex w-full rounded-lg px-4 py-3 text-base font-medium text-muted transition-colors hover:bg-panel2 hover:text-text focus-visible:bg-panel2 focus-visible:text-text focus-visible:outline-none"
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
