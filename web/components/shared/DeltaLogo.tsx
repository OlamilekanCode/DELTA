export default function DeltaLogo({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#9B7BFF" />
          <stop offset="100%" stopColor="#3D7BFF" />
        </linearGradient>
        <filter id="logo-glow">
          <feGaussianBlur stdDeviation="1" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <polygon points="16,5 28,27 4,27" fill="url(#logo-grad)" opacity="0.18" filter="url(#logo-glow)" />
      <polygon points="16,5 28,27 4,27" fill="none" stroke="url(#logo-grad)" strokeWidth="2" strokeLinejoin="round" filter="url(#logo-glow)" />
      <line x1="10" y1="27" x2="22" y2="27" stroke="url(#logo-grad)" strokeWidth="0.8" opacity="0.5" />
    </svg>
  );
}
