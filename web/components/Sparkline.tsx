// A scenario's shape: whole numbers 0 to 100 from the API (`shape`), drawn as a line with a soft fill. Decorative: the card's text says the
// same thing in words, so screen readers skip it. Coordinates are drawing positions only. Scale: every card uses the SAME vertical scale
// (the engine's shared log scale, DESIGN.md §10), so one height means one relative change on every card; the dashed line is the starting level.
export function Sparkline({ shape, label }: { shape: number[]; label?: string }) {
  const w = 120, h = 96, pad = 4;
  const last = shape.length > 1 ? shape.length - 1 : 1;
  const y = (v: number) => h - pad - (v * (h - 2 * pad)) / 100;
  const pts = shape.map((v, i) => `${pad + (i * (w - 2 * pad)) / last},${y(v)}`);
  return (
    <svg className="spark decor" viewBox={`0 0 ${w} ${h}`} width="100%" height={h} preserveAspectRatio="none" aria-hidden="true" focusable="false" data-label={label}>
      <line className="spark-base" x1={pad} x2={w - pad} y1={y(shape[0] ?? 0)} y2={y(shape[0] ?? 0)} strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
      <polygon points={`${pad},${h - pad} ${pts.join(" ")} ${w - pad},${h - pad}`} className="spark-fill" />
      <polyline points={pts.join(" ")} className="spark-line" fill="none" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
