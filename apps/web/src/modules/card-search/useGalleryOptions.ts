import { computed } from 'vue';
import { useLocalStorage } from '@vueuse/core';

type GalleryOptionsState = {
  tooltipEnabled: boolean;
  cardScale: number;
};

const DEFAULT_OPTIONS: GalleryOptionsState = {
  tooltipEnabled: true,
  cardScale: 1,
};

const clampScale = (value: number): number => Math.min(1.2, Math.max(0.8, value));

export const useGalleryOptions = () => {
  const storedOptions = useLocalStorage<GalleryOptionsState>('card-reader.gallery-options', DEFAULT_OPTIONS, {
    mergeDefaults: true,
  });

  const tooltipEnabled = computed({
    get: () => storedOptions.value.tooltipEnabled,
    set: (value: boolean) => {
      storedOptions.value = {
        ...storedOptions.value,
        tooltipEnabled: value,
      };
    },
  });

  const cardScale = computed({
    get: () => clampScale(storedOptions.value.cardScale),
    set: (value: number) => {
      storedOptions.value = {
        ...storedOptions.value,
        cardScale: clampScale(value),
      };
    },
  });

  return {
    tooltipEnabled,
    cardScale,
  };
};
