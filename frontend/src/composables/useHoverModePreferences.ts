import { computed } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import { DEFAULT_HOVER_MODE, isHoverMode, type HoverMode } from '@/composables/card-gallery/hoverMode';
import { DEFAULT_HOVER_PREVIEW_SCALE, normalizeHoverPreviewScale } from '@/composables/card-gallery/hoverPreviewScale';
import { GALLERY_OPTIONS_STORAGE_KEY } from '@/composables/useGalleryOptions';

export type HoverModeSurface = 'gallery' | 'deckBuilder' | 'deckDetail';

type HoverModeOverrideState = Record<HoverModeSurface, HoverMode | null>;

type LegacyGalleryOptionsState = {
  hoverMode?: unknown;
  tooltipEnabled?: boolean;
};

const DEFAULT_OVERRIDES: HoverModeOverrideState = {
  gallery: null,
  deckBuilder: null,
  deckDetail: null,
};

const normalizeHoverMode = (value: unknown): HoverMode => (isHoverMode(value) ? value : DEFAULT_HOVER_MODE);

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

export const useHoverModePreferences = () => {
  const storedDefaultHoverMode = useLocalStorage<HoverMode | null>('card-reader.default-hover-mode', null);
  const storedHoverPreviewScale = useLocalStorage<number>('card-reader.hover-preview-scale', DEFAULT_HOVER_PREVIEW_SCALE);
  const storedOverrides = useLocalStorage<HoverModeOverrideState>('card-reader.hover-mode-overrides', DEFAULT_OVERRIDES, {
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

export const useHoverModeSurface = (surface: HoverModeSurface) => {
  const preferences = useHoverModePreferences();
  const overrideHoverMode = preferences.getOverrideHoverMode(surface);
  const effectiveHoverMode = preferences.getEffectiveHoverMode(surface);

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
