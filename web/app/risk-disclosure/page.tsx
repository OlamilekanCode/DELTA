import type { Metadata } from "next";
import ComingSoonShell from "@/components/shared/ComingSoonShell";

export const metadata: Metadata = {
  title: "Risk Disclosure — DELTA",
};

const icon = (
  <svg className="size-9" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
  </svg>
);

export default function RiskDisclosurePage() {
  return (
    <ComingSoonShell
      title="Risk Disclosure"
      description="Risk Disclosure will be available before the public launch of DELTA. DELTA Exposure Scores are for informational purposes only and do not constitute investment advice."
      icon={icon}
      backHref="/methodology"
      backLabel="Read the methodology"
    />
  );
}
