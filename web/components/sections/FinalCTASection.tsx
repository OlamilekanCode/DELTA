import Link from "next/link";
import SectionReveal from "@/components/shared/SectionReveal";

export default function FinalCTASection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8" aria-labelledby="cta-heading">
      <SectionReveal>
        <div className="relative overflow-hidden rounded-3xl border border-violet/20 bg-panel px-8 py-16 text-center sm:px-16">
          {/* Background glow */}
          <div
            className="pointer-events-none absolute inset-0"
            aria-hidden="true"
            style={{
              background:
                "radial-gradient(ellipse at 50% 0%, rgba(109,74,255,0.15) 0%, transparent 70%)",
            }}
          />

          <p className="relative mb-4 font-mono text-xs font-medium uppercase tracking-[0.2em] text-violet">
            Start now — free
          </p>
          <h2
            id="cta-heading"
            className="relative font-heading text-4xl font-bold text-text sm:text-5xl"
          >
            Map the market today.
          </h2>
          <p className="relative mx-auto mt-5 max-w-md text-lg text-muted">
            Explore the free NVDA example, then connect your wallet to unlock the full platform.
          </p>

          <div className="relative mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/asset/NVDA"
              className="inline-flex items-center gap-2 rounded-xl bg-violet px-8 py-4 text-base font-semibold text-white shadow-xl shadow-violet/30 transition-all hover:bg-violet-light hover:shadow-violet/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet active:scale-95"
            >
              Explore NVDA
              <svg className="size-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </Link>

            <Link
              href="/methodology"
              className="inline-flex items-center gap-2 rounded-xl border border-white/[0.09] bg-panel2 px-8 py-4 text-base font-semibold text-text transition-all hover:border-violet/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet active:scale-95"
            >
              How it works
            </Link>
          </div>
        </div>
      </SectionReveal>
    </section>
  );
}
