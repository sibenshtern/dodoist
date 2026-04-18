const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/;
const FALLBACK_RGBA_PREFIX = 'rgba(107,114,128,'; // neutral gray

/** Converts a 6-digit hex color to rgba with the given alpha. Falls back to gray. */
export function hexToRgba(hex: string, alpha: number): string {
  if (!HEX_COLOR_RE.test(hex)) {
    return `${FALLBACK_RGBA_PREFIX}${alpha})`;
  }
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
