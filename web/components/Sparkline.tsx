// A scenario's shape: whole numbers 0 to 100 from the API (`shape`), drawn as a line with a soft fill. Decorative: the card's text says the
// same thing in words, so screen readers skip it. Coordinates are drawing positions only.
export function Sparkline({ shape, label }: { shape: number[]; label?: string }) {
  const w = 120, h = 36, pad = 3;
  const last = shape.length > 1 ? shape.length - 1 : 1;
  const pts = shape.map((v, i) => `${pad + (i * (w - 2 * pad)) / last},${h - pad - (v * (h - 2 * pad)) / 100}`);
  return (
    <svg className="spark decor" viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none" aria-hidden="true" focusable="false" data-label={label}>
      <polygon points={`${pad},${h - pad} ${pts.join(" ")} ${w - pad},${h - pad}`} className="spark-fill" />
      <polyline points={pts.join(" ")} className="spark-line" fill="none" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
