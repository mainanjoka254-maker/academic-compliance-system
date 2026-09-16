export function letterFromPercentage(pct: number) {
  if (pct >= 70) return { letter: "A", points: 5 };
  if (pct >= 60) return { letter: "B", points: 4 };
  if (pct >= 50) return { letter: "C", points: 3 };
  if (pct >= 40) return { letter: "D", points: 2 };
  return { letter: "F", points: 0 };
}

export function safeNumber(value: unknown, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}
