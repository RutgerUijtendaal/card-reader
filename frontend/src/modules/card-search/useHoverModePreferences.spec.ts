import { beforeEach, describe, expect, test } from 'vitest';
import { nextTick } from 'vue';
import { DEFAULT_HOVER_MODE } from '@/modules/card-search/hoverMode';
import { GALLERY_OPTIONS_STORAGE_KEY } from '@/modules/card-search/useGalleryOptions';
import { useHoverModePreferences, useHoverModeSurface } from '@/modules/card-search/useHoverModePreferences';

describe('useHoverModePreferences', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('defaults to the shared hover mode default', () => {
    const { defaultHoverMode } = useHoverModePreferences();

    expect(defaultHoverMode.value).toBe(DEFAULT_HOVER_MODE);
  });

  test('maps legacy tooltipEnabled=true to details', () => {
    localStorage.setItem(
      GALLERY_OPTIONS_STORAGE_KEY,
      JSON.stringify({
        tooltipEnabled: true,
        cardScale: 1,
        showCardGroups: true,
        pageSize: 30,
      }),
    );

    const { defaultHoverMode } = useHoverModePreferences();

    expect(defaultHoverMode.value).toBe('details');
  });

  test('maps legacy tooltipEnabled=false to none', () => {
    localStorage.setItem(
      GALLERY_OPTIONS_STORAGE_KEY,
      JSON.stringify({
        tooltipEnabled: false,
        cardScale: 1,
        showCardGroups: true,
        pageSize: 30,
      }),
    );

    const { defaultHoverMode } = useHoverModePreferences();

    expect(defaultHoverMode.value).toBe('none');
  });

  test('surface override falls back to the global default when unset', async () => {
    const { defaultHoverMode } = useHoverModePreferences();
    const gallery = useHoverModeSurface('gallery');

    expect(gallery.effectiveHoverMode.value).toBe(DEFAULT_HOVER_MODE);

    defaultHoverMode.value = 'enlarged';
    await nextTick();

    expect(gallery.overrideHoverMode.value).toBeNull();
    expect(gallery.effectiveHoverMode.value).toBe('enlarged');
  });

  test('surface override does not rewrite the global default', async () => {
    const { defaultHoverMode } = useHoverModePreferences();
    const deckBuilder = useHoverModeSurface('deckBuilder');

    defaultHoverMode.value = 'details';
    deckBuilder.setOverrideHoverMode('enlarged-details');
    await nextTick();

    expect(defaultHoverMode.value).toBe('details');
    expect(deckBuilder.overrideHoverMode.value).toBe('enlarged-details');
    expect(deckBuilder.effectiveHoverMode.value).toBe('enlarged-details');

    deckBuilder.clearOverrideHoverMode();
    await nextTick();

    expect(deckBuilder.overrideHoverMode.value).toBeNull();
    expect(deckBuilder.effectiveHoverMode.value).toBe('details');
  });
});
