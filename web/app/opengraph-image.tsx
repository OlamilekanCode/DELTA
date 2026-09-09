import { ImageResponse } from "next/og";

export const runtime = "nodejs";
export const alt = "Synthetic Exposure — map how stocks and crypto move together";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#030508",
          fontFamily: "sans-serif",
        }}
      >
        {/* Subtle radial glow */}
        <div
          style={{
            position: "absolute",
            width: 600,
            height: 600,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(155,123,255,0.12) 0%, transparent 70%)",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          }}
        />

        {/* Brand mark triangle SVG */}
        <svg width="120" height="120" viewBox="0 0 32 32">
          <defs>
            <linearGradient id="dg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#9B7BFF" />
              <stop offset="100%" stopColor="#3D7BFF" />
            </linearGradient>
          </defs>
          <polygon
            points="16,5 28,27 4,27"
            fill="url(#dg)"
            opacity="0.18"
          />
          <polygon
            points="16,5 28,27 4,27"
            fill="none"
            stroke="url(#dg)"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <line
            x1="10"
            y1="27"
            x2="22"
            y2="27"
            stroke="url(#dg)"
            strokeWidth="0.8"
            opacity="0.5"
          />
        </svg>

        {/* Brand name */}
        <div
          style={{
            marginTop: 32,
            fontSize: 72,
            fontWeight: 700,
            letterSpacing: "-2px",
            background: "linear-gradient(135deg, #9B7BFF 0%, #3D7BFF 100%)",
            backgroundClip: "text",
            color: "transparent",
          }}
        >
          Synthetic Exposure
        </div>

        {/* Tagline */}
        <div
          style={{
            marginTop: 16,
            fontSize: 28,
            color: "#8B92A8",
            letterSpacing: "0.5px",
          }}
        >
          Map how stocks and crypto move together
        </div>
      </div>
    ),
    { ...size },
  );
}
