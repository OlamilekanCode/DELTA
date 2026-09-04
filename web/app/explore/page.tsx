import type { Metadata } from "next";
import Link from "next/link";
import ComingSoonShell from "@/components/shared/ComingSoonShell";

export const metadata: Metadata = {
  title: "Explore — DELTA",
  description: "Search supported stocks and discover connected crypto assets by Exposure Score.",
};

const icon = (
  <svg className="size-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
  </svg>
);

export default function ExplorePage() {
  return (
    <>
      <ComingSoonShell
        title="Explore Stocks & Crypto"
        description="Full asset search and discovery across stocks and crypto is on the way. In the meantime, explore the free NVDA example on the home page."
        icon={icon}
        backHref="/asset/NVDA"
        backLabel="See the NVDA example"
      />
      <div className="mx-auto max-w-7xl px-6 pb-16 lg:px-8">
        <p className="text-center text-sm text-muted">
          Or{" "}
          <Link href="/" className="text-violet-light underline underline-offset-4 hover:text-violet">
            return to the home page
          </Link>
        </p>
      </div>
    </>
  );
}
