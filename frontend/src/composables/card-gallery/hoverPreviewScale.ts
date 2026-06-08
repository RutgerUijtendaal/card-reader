export const DEFAULT_HOVER_PREVIEW_SCALE = 1;
export const HOVER_PREVIEW_SCALE_MIN = 0.8;
export const HOVER_PREVIEW_SCALE_MAX = 1.2;
export const HOVER_PREVIEW_SCALE_STEP = 0.05;

export const normalizeHoverPreviewScale = (value: unknown): number => {
  const numericValue = typeof value === 'number'
    ? value
    : typeof value === 'string'
      ? Number(value)
      : Number.NaN;

  if (Number.isNaN(numericValue)) {
    return DEFAULT_HOVER_PREVIEW_SCALE;
  }
  return Math.min(HOVER_PREVIEW_SCALE_MAX, Math.max(HOVER_PREVIEW_SCALE_MIN, numericValue));
};
