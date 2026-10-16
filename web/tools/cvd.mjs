// Colour-vision-deficiency simulation for hex colours: Machado, Oliveira and Fernandes (2009), "A Physiologically-based Model for
// Simulation of Color Vision Deficiency", IEEE TVCG 15(6), matrices at severity 1.0 (dichromacy), from
// https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html . The matrices are applied to LINEAR RGB (the sRGB
// values are decoded first and re-encoded after), which is the paper's model; the page itself does not say so, the paper does.
// Colour difference: CIE76 delta E in CIELAB (D65). Used by tests/contrast.test.ts and by e2e/cvd-shots.mjs for the screenshots.
export const MATRICES = {
  protanopia: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deuteranopia: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]],
  tritanopia: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.3039]],
};
const toLin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const toSrgb = (l) => { l = Math.min(1, Math.max(0, l)); return 255 * (l <= 0.0031308 ? 12.92 * l : 1.055 * l ** (1 / 2.4) - 0.055); };
export const rgb = (h) => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
export const hex = (v) => "#" + v.map((x) => Math.round(x).toString(16).padStart(2, "0")).join("");
export function simulate(h, kind) {
  const m = MATRICES[kind], lin = rgb(h).map(toLin);
  return hex(m.map((row) => toSrgb(row[0] * lin[0] + row[1] * lin[1] + row[2] * lin[2])));
}
export function lab(h) {
  const [r, g, b] = rgb(h).map(toLin);
  const X = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047, Y = 0.2126729 * r + 0.7151522 * g + 0.072175 * b,
    Z = (0.0193339 * r + 0.119192 * g + 0.9503041 * b) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
}
export const deltaE = (a, b) => Math.hypot(...lab(a).map((x, i) => x - lab(b)[i]));
/** Lightness difference (CIE L*) between two colours. */
export const dL = (a, b) => Math.abs(lab(a)[0] - lab(b)[0]);
