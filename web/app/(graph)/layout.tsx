import type React from "react";

export default function GraphLayout({ children }: { children: React.ReactNode }) {
  return <div className="h-screen overflow-hidden bg-bg text-text">{children}</div>;
}
