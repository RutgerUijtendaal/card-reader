import { computed, type ComputedRef, type WritableComputedRef } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import { DEFAULT_HOVER_MODE, isHoverMode, type HoverMode } from '@/composables/card-gallery/hoverMode';
import {
  DEFAULT_HOVER_PREVIEW_SCALE,
  HOVER_PREVIEW_SCALE_STEP,
  normalizeHoverPreviewScale,
} from '@/composables/card-gallery/hoverPreviewScale';
import { GALLERY_OPTIONS_STORAGE_KEY } from '@/composables/useGalleryOptions';

export type HoverModeSurface = 'gallery' | 'deckBuilder' | 'deckDetail';

type HoverModeOverrideState = Record<HoverModeSurface, HoverMode | null>;

type LegacyGalleryOptionsState = {
  hoverMode?: unknown;
  tooltipEnabled?: boolean;
};

type HoverModePreferencesState = {
  defaultHoverMode: WritableComputedRef<HoverMode>;
  hoverPreviewScale: WritableComputedRef<number>;
  getOverrideHoverMode: (surface: HoverModeSurface) => WritableComputedRef<HoverMode | null>;
  getEffectiveHoverMode: (surface: HoverModeSurface) => ComputedRef<HoverMode>;
};

const DEFAULT_OVERRIDES: HoverModeOverrideState = {
  gallery: null,
  deckBuilder: null,
  deckDetail: null,
};
const HOVER_MODE_OVERRIDES_STORAGE_KEY = 'card-reader.hover-mode-overrides';
let hoverModePreferencesState: HoverModePreferencesState | null = null;

const normalizeHoverMode = (value: unknown): HoverMode => (isHoverMode(value) ? value : DEFAULT_HOVER_MODE);

export const resolveHoverModeSurfacePath = (path: string): HoverModeSurface | null => {
  if (path === '/cards') {
    return 'gallery';
  }
  if (path === '/my/decks/new' || /^\/my\/decks\/[^/]+\/edit$/.test(path)) {
    return 'deckBuilder';
  }
  if (/^\/decks\/[^/]+$/.test(path) || /^\/my\/decks\/[^/]+$/.test(path)) {
    return 'deckDetail';
  }
  return null;
};

export const getHoverPreviewScaleForWheelDelta = (currentScale: number, deltaY: number): number => {
  if (deltaY === 0) {
    return normalizeHoverPreviewScale(currentScale);
  }

  const direction = deltaY < 0 ? 1 : -1;
  const nextScale = normalizeHoverPreviewScale(currentScale) + direction * HOVER_PREVIEW_SCALE_STEP;
  return normalizeHoverPreviewScale(Number(nextScale.toFixed(2)));
};

export const handleHoverPreviewScaleWheel = (
  event: Pick<WheelEvent, 'altKey' | 'deltaY' | 'preventDefault'>,
  currentScale: number,
  setScale: (scale: number) => void,
): boolean => {
  if (!event.altKey) {
    return false;
  }

  event.preventDefault();
  setScale(getHoverPreviewScaleForWheelDelta(currentScale, event.deltaY));
  return true;
};

const readLegacyDefaultHoverMode = (): HoverMode => {
  const stored = localStorage.getItem(GALLERY_OPTIONS_STORAGE_KEY);
  if (!stored) {
    return DEFAULT_HOVER_MODE;
  }

  try {
    const parsed = JSON.parse(stored) as LegacyGalleryOptionsState;
    if (typeof parsed.tooltipEnabled === 'boolean') {
      return parsed.tooltipEnabled ? 'details' : 'none';
    }
    return normalizeHoverMode(parsed.hoverMode);
  } catch {
    return DEFAULT_HOVER_MODE;
  }
};

const createHoverModePreferencesState = (): HoverModePreferencesState => {
  const storedDefaultHoverMode = useLocalStorage<HoverMode | null>('card-reader.default-hover-mode', null);
  const storedHoverPreviewScale = useLocalStorage<number>('card-reader.hover-preview-scale', DEFAULT_HOVER_PREVIEW_SCALE);
  const storedOverrides = useLocalStorage<HoverModeOverrideState>(HOVER_MODE_OVERRIDES_STORAGE_KEY, DEFAULT_OVERRIDES, {
    mergeDefaults: true,
  });

  const defaultHoverMode = computed<HoverMode>({
    get: () => normalizeHoverMode(storedDefaultHoverMode.value ?? readLegacyDefaultHoverMode()),
    set: (value) => {
      storedDefaultHoverMode.value = normalizeHoverMode(value);
    },
  });

  const getOverrideHoverMode = (surface: HoverModeSurface) =>
    computed<HoverMode | null>({
      get: () => {
        const value = storedOverrides.value[surface];
        return value === null ? null : normalizeHoverMode(value);
      },
      set: (value) => {
        storedOverrides.value = {
          ...storedOverrides.value,
          [surface]: value === null ? null : normalizeHoverMode(value),
        };
      },
    });

  const getEffectiveHoverMode = (surface: HoverModeSurface) => {
    const overrideHoverMode = getOverrideHoverMode(surface);
    return computed<HoverMode>(() => overrideHoverMode.value ?? defaultHoverMode.value);
  };

  const hoverPreviewScale = computed({
    get: () => normalizeHoverPreviewScale(storedHoverPreviewScale.value),
    set: (value: number) => {
      storedHoverPreviewScale.value = normalizeHoverPreviewScale(value);
    },
  });

  return {
    defaultHoverMode,
    hoverPreviewScale,
    getOverrideHoverMode,
    getEffectiveHoverMode,
  };
};

export const useHoverModePreferences = (): HoverModePreferencesState => {
  hoverModePreferencesState ??= createHoverModePreferencesState();
  return hoverModePreferencesState;
};

export const __resetHoverModePreferencesForTests = (): void => {
  hoverModePreferencesState = null;
};

export const useHoverModeSurface = (surface: HoverModeSurface) => {
  const preferences = useHoverModePreferences();
  const overrideHoverMode = preferences.getOverrideHoverMode(surface);
  const effectiveHoverMode = computed<HoverMode>(() => overrideHoverMode.value ?? preferences.defaultHoverMode.value);

  const setOverrideHoverMode = (value: HoverMode): void => {
    overrideHoverMode.value = value;
  };

  const clearOverrideHoverMode = (): void => {
    overrideHoverMode.value = null;
  };

  return {
    defaultHoverMode: preferences.defaultHoverMode,
    hoverPreviewScale: preferences.hoverPreviewScale,
    overrideHoverMode,
    effectiveHoverMode,
    setOverrideHoverMode,
    clearOverrideHoverMode,
  };
};
