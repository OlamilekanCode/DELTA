const MINUS = "\u2212"; // proper minus sign (U+2212), not a hyphen

export function formatScore(score: number): string {
  if (score === 0 || Object.is(score, -0)) return "0.00";
  const abs = Math.abs(score).toFixed(2);
  return score > 0 ? `+${abs}` : `${MINUS}${abs}`;
}
