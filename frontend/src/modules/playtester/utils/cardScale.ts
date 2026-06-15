const PLAYTEST_CARD_SCALE_STORAGE_KEY = 'card-reader.playtester.card-scale';

export const PLAYTEST_CARD_SCALE_DEFAULT = 0.75;
export const PLAYTEST_CARD_SCALE_MIN = 0.5;
export const PLAYTEST_CARD_SCALE_MAX = 1.6;
export const PLAYTEST_CARD_SCALE_STEP = 0.05;

const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

export const normalizePlaytestCardScale = (value: number): number =>
  clamp(
    Math.round(value / PLAYTEST_CARD_SCALE_STEP) * PLAYTEST_CARD_SCALE_STEP,
    PLAYTEST_CARD_SCALE_MIN,
    PLAYTEST_CARD_SCALE_MAX,
  );

export const loadPlaytestCardScale = (): number => {
  if (typeof localStorage === 'undefined') {
    return PLAYTEST_CARD_SCALE_DEFAULT;
  }
  const raw = localStorage.getItem(PLAYTEST_CARD_SCALE_STORAGE_KEY);
  const value = raw ? Number.parseFloat(raw) : Number.NaN;
  return Number.isFinite(value) ? normalizePlaytestCardScale(value) : PLAYTEST_CARD_SCALE_DEFAULT;
};

export const savePlaytestCardScale = (value: number): void => {
  if (typeof localStorage === 'undefined') {
    return;
  }
  localStorage.setItem(PLAYTEST_CARD_SCALE_STORAGE_KEY, String(normalizePlaytestCardScale(value)));
};

export const getPlaytestCardScaleStyle = (scale: number): Record<string, string> => ({
  '--playtest-card-width': `${(9.75 * scale).toFixed(2)}rem`,
  '--playtest-compact-card-width': `${(6.15 * scale).toFixed(2)}rem`,
  '--playtest-stack-full-width': `${(11.35 * scale).toFixed(2)}rem`,
  '--playtest-stack-button-width': `${(3.25 * Math.min(scale, 1.12)).toFixed(2)}rem`,
});
