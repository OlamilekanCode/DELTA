import type React from "react";
import Navigation from "@/components/nav/Navigation";
import Footer from "@/components/shared/Footer";

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-full flex-col">
      <Navigation />
      <main className="flex-1 pt-20">{children}</main>
      <Footer />
    </div>
  );
}
