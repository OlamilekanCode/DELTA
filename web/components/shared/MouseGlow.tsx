"use client";

import { useEffect, useRef } from "react";

export default function MouseGlow() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let animId = 0;
    let tx = -600, ty = -600;
    let cx = -600, cy = -600;

    const onMove = (e: MouseEvent) => { tx = e.clientX; ty = e.clientY; };
    window.addEventListener("mousemove", onMove, { passive: true });

    const tick = () => {
      cx += (tx - cx) * 0.08;
      cy += (ty - cy) * 0.08;
      el.style.transform = `translate(${cx - 300}px,${cy - 300}px)`;
      animId = requestAnimationFrame(tick);
    };
    animId = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(animId);
    };
  }, []);

  return (
    <div
      ref={ref}
      className="pointer-events-none fixed left-0 top-0 z-[9998]"
      style={{
        width: 600,
        height: 600,
        background:
          "radial-gradient(circle, rgba(109,74,255,0.18) 0%, rgba(109,74,255,0.08) 40%, transparent 70%)",
        willChange: "transform",
      }}
      aria-hidden="true"
    />
  );
}
