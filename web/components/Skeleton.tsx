// Placeholder blocks while the API answers. Decorative and silent: the page announces loading through a status message, not through these.
export function Skeleton({ height = 16, width = "100%", radius = 8 }: { height?: number; width?: number | string; radius?: number }) {
  return <span className="skeleton decor" aria-hidden="true" style={{ height, width, borderRadius: radius }} />;
}
