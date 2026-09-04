import Link from "next/link";

interface ComingSoonShellProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  backHref?: string;
  backLabel?: string;
}

export default function ComingSoonShell({
  title,
  description,
  icon,
  backHref = "/",
  backLabel = "Back to home",
}: ComingSoonShellProps) {
  return (
    <section className="flex min-h-[70vh] flex-col items-center justify-center px-6 py-24 text-center">
      <div className="mb-6 flex size-20 items-center justify-center rounded-2xl border border-white/[0.09] bg-panel2 text-violet">
        {icon}
      </div>

      <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet/30 bg-violet/10 px-3 py-1 text-xs font-medium text-violet-light">
        <span className="size-1.5 rounded-full bg-violet-light" aria-hidden="true" />
        Coming soon
      </div>

      <h1 className="mt-4 font-heading text-3xl font-bold text-text sm:text-4xl">{title}</h1>
      <p className="mt-4 max-w-md text-base text-muted">{description}</p>

      <Link
        href={backHref}
        className="mt-10 inline-flex items-center gap-2 rounded-lg border border-white/[0.09] bg-panel px-5 py-2.5 text-sm font-medium text-text transition-colors hover:border-violet/50 hover:bg-panel2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet"
      >
        <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        {backLabel}
      </Link>
    </section>
  );
}
