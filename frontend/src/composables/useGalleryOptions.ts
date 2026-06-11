import { computed } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import { DEFAULT_CARD_PAGE_SIZE, normalizeCardPageSize } from '@/composables/card-gallery/pageSize';

export const GALLERY_OPTIONS_STORAGE_KEY = 'card-reader.gallery-options';
export const GALLERY_CARD_SCALE_MIN = 0.6;
export const GALLERY_CARD_SCALE_MAX = 1.4;
export const GALLERY_CARD_SCALE_STEP = 0.05;

type GalleryOptionsState = {
  cardScale: number;
  showCardGroups: boolean;
  pageSize: number;
};

type LegacyGalleryOptionsState = Partial<GalleryOptionsState> & {
  hoverMode?: unknown;
  tooltipEnabled?: boolean;
};

const DEFAULT_OPTIONS: GalleryOptionsState = {
  cardScale: 1,
  showCardGroups: true,
  pageSize: DEFAULT_CARD_PAGE_SIZE,
};

const clampScale = (value: number): number =>
  Math.min(GALLERY_CARD_SCALE_MAX, Math.max(GALLERY_CARD_SCALE_MIN, value));

const normalizeStoredOptions = (value: LegacyGalleryOptionsState | null | undefined): GalleryOptionsState => ({
  cardScale: clampScale(value?.cardScale ?? DEFAULT_OPTIONS.cardScale),
  showCardGroups: value?.showCardGroups ?? DEFAULT_OPTIONS.showCardGroups,
  pageSize: normalizeCardPageSize(value?.pageSize ?? DEFAULT_OPTIONS.pageSize),
});

export const useGalleryOptions = () => {
  const storedOptions = useLocalStorage<LegacyGalleryOptionsState>(GALLERY_OPTIONS_STORAGE_KEY, DEFAULT_OPTIONS, {
    mergeDefaults: true,
  });

  const cardScale = computed({
    get: () => normalizeStoredOptions(storedOptions.value).cardScale,
    set: (value: number) => {
      const normalized = normalizeStoredOptions(storedOptions.value);
      storedOptions.value = {
        ...storedOptions.value,
        ...normalized,
        cardScale: clampScale(value),
      };
    },
  });

  const showCardGroups = computed({
    get: () => normalizeStoredOptions(storedOptions.value).showCardGroups,
    set: (value: boolean) => {
      const normalized = normalizeStoredOptions(storedOptions.value);
      storedOptions.value = {
        ...storedOptions.value,
        ...normalized,
        showCardGroups: value,
      };
    },
  });

  const pageSize = computed({
    get: () => normalizeStoredOptions(storedOptions.value).pageSize,
    set: (value: number) => {
      const normalized = normalizeStoredOptions(storedOptions.value);
      storedOptions.value = {
        ...storedOptions.value,
        ...normalized,
        pageSize: normalizeCardPageSize(value),
      };
    },
  });

  return {
    cardScale,
    showCardGroups,
    pageSize,
  };
};
