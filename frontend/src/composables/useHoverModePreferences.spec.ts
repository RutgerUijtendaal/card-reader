import { beforeEach, describe, expect, test, vi } from 'vitest';
import { nextTick } from 'vue';
import { DEFAULT_HOVER_MODE } from '@/composables/card-gallery/hoverMode';
import { DEFAULT_HOVER_PREVIEW_SCALE } from '@/composables/card-gallery/hoverPreviewScale';
import { GALLERY_OPTIONS_STORAGE_KEY } from '@/composables/useGalleryOptions';
import {
  __resetHoverModePreferencesForTests,
  getHoverPreviewScaleForWheelDelta,
  handleHoverPreviewScaleWheel,
  resolveHoverModeSurfacePath,
  useHoverModePreferences,
  useHoverModeSurface,
} from '@/composables/useHoverModePreferences';

describe('useHoverModePreferences', () => {
  beforeEach(() => {
    __resetHoverModePreferencesForTests();
    localStorage.clear();
  });

  test('defaults to the shared hover mode default', () => {
    const { defaultHoverMode, hoverPreviewScale } = useHoverModePreferences();

    expect(defaultHoverMode.value).toBe(DEFAULT_HOVER_MODE);
    expect(hoverPreviewScale.value).toBe(DEFAULT_HOVER_PREVIEW_SCALE);
  });

  test('stores the hover preview scale within the supported range', async () => {
    const { hoverPreviewScale } = useHoverModePreferences();

    hoverPreviewScale.value = 1.15;
    await nextTick();

    expect(hoverPreviewScale.value).toBe(1.15);

    hoverPreviewScale.value = '1.05' as unknown as number;
    await nextTick();

    expect(hoverPreviewScale.value).toBe(1.05);

    hoverPreviewScale.value = 2;
    await nextTick();

    expect(hoverPreviewScale.value).toBe(1.2);

    hoverPreviewScale.value = 0.2;
    await nextTick();

    expect(hoverPreviewScale.value).toBe(0.8);
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

  test('surface override changes stay scoped to the selected surface', async () => {
    const preferences = useHoverModePreferences();
    const galleryOverride = preferences.getOverrideHoverMode('gallery');
    const deckDetailOverride = preferences.getOverrideHoverMode('deckDetail');
    const galleryEffective = preferences.getEffectiveHoverMode('gallery');
    const deckDetailEffective = preferences.getEffectiveHoverMode('deckDetail');

    preferences.defaultHoverMode.value = 'details';
    galleryOverride.value = 'none';
    deckDetailOverride.value = 'enlarged';
    await nextTick();

    expect(galleryEffective.value).toBe('none');
    expect(deckDetailEffective.value).toBe('enlarged');

    galleryOverride.value = 'enlarged-details';
    await nextTick();

    expect(galleryEffective.value).toBe('enlarged-details');
    expect(deckDetailEffective.value).toBe('enlarged');

    galleryOverride.value = null;
    await nextTick();

    expect(galleryOverride.value).toBeNull();
    expect(galleryEffective.value).toBe('details');
    expect(deckDetailEffective.value).toBe('enlarged');
  });

  test('surface override writes preserve newer changes from other preference instances', async () => {
    const firstPreferences = useHoverModePreferences();
    const secondPreferences = useHoverModePreferences();
    const firstGalleryOverride = firstPreferences.getOverrideHoverMode('gallery');
    const secondDeckBuilderOverride = secondPreferences.getOverrideHoverMode('deckBuilder');

    secondDeckBuilderOverride.value = 'enlarged';
    await nextTick();

    firstGalleryOverride.value = 'none';
    await nextTick();

    const stored = JSON.parse(localStorage.getItem('card-reader.hover-mode-overrides') ?? '{}') as Record<string, unknown>;
    expect(stored).toMatchObject({
      gallery: 'none',
      deckBuilder: 'enlarged',
    });
  });

  test('resolves route paths to hover mode surfaces', () => {
    expect(resolveHoverModeSurfacePath('/cards')).toBe('gallery');
    expect(resolveHoverModeSurfacePath('/decks/deck-1')).toBe('deckDetail');
    expect(resolveHoverModeSurfacePath('/my/decks/deck-1')).toBe('deckDetail');
    expect(resolveHoverModeSurfacePath('/my/decks/new')).toBe('deckBuilder');
    expect(resolveHoverModeSurfacePath('/my/decks/deck-1/edit')).toBe('deckBuilder');
    expect(resolveHoverModeSurfacePath('/cards/card-1')).toBeNull();
    expect(resolveHoverModeSurfacePath('/settings')).toBeNull();
  });

  test('wheel delta adjusts hover preview scale by one bounded step', () => {
    expect(getHoverPreviewScaleForWheelDelta(1, -100)).toBe(1.05);
    expect(getHoverPreviewScaleForWheelDelta(1, 100)).toBe(0.95);
    expect(getHoverPreviewScaleForWheelDelta(1.2, -100)).toBe(1.2);
    expect(getHoverPreviewScaleForWheelDelta(0.8, 100)).toBe(0.8);
    expect(getHoverPreviewScaleForWheelDelta(1.05, 0)).toBe(1.05);
  });

  test('alt wheel prevents default and updates hover preview scale', () => {
    let scale = 1;
    const preventDefault = vi.fn();

    expect(handleHoverPreviewScaleWheel({ altKey: true, deltaY: -100, preventDefault }, scale, (value) => {
      scale = value;
    })).toBe(true);

    expect(preventDefault).toHaveBeenCalledOnce();
    expect(scale).toBe(1.05);
  });

  test('normal wheel does not prevent default or update hover preview scale', () => {
    let scale = 1;
    const preventDefault = vi.fn();

    expect(handleHoverPreviewScaleWheel({ altKey: false, deltaY: -100, preventDefault }, scale, (value) => {
      scale = value;
    })).toBe(false);

    expect(preventDefault).not.toHaveBeenCalled();
    expect(scale).toBe(1);
  });
});
