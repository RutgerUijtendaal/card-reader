import { beforeEach, describe, expect, test } from 'vitest';
import { nextTick } from 'vue';
import { GALLERY_OPTIONS_STORAGE_KEY, useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModePreferences } from '@/composables/useHoverModePreferences';

describe('useGalleryOptions', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('preserves legacy hover keys when updating unrelated gallery options', async () => {
    localStorage.setItem(
      GALLERY_OPTIONS_STORAGE_KEY,
      JSON.stringify({
        tooltipEnabled: false,
        cardScale: 1,
        showCardGroups: true,
        pageSize: 30,
      }),
    );

    const { cardScale } = useGalleryOptions();
    cardScale.value = 1.1;
    await nextTick();

    const stored = JSON.parse(localStorage.getItem(GALLERY_OPTIONS_STORAGE_KEY) ?? '{}') as {
      tooltipEnabled?: boolean;
    };

    expect(stored.tooltipEnabled).toBe(false);
    expect(useHoverModePreferences().defaultHoverMode.value).toBe('none');
  });

  test('clamps card scale to the supported gallery range', async () => {
    const { cardScale } = useGalleryOptions();

    cardScale.value = 1.4;
    await nextTick();
    expect(cardScale.value).toBe(1.4);

    cardScale.value = 2;
    await nextTick();
    expect(cardScale.value).toBe(1.4);

    cardScale.value = 0.2;
    await nextTick();
    expect(cardScale.value).toBe(0.6);
  });
});
