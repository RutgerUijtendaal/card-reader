import { beforeEach, describe, expect, test } from 'vitest';
import { nextTick } from 'vue';
import {
  CARD_SORT_PREFERENCES_STORAGE_KEY,
  LEGACY_CARD_SORT_OVERRIDES_STORAGE_KEY,
  LEGACY_DEFAULT_CARD_SORT_STORAGE_KEY,
  migrateCardSortPreferences,
  useCardSortPreferences,
  useCardSortSurface,
} from '@/domain/cards/composables/useCardSortPreferences';

const storedPreferences = () => JSON.parse(
  localStorage.getItem(CARD_SORT_PREFERENCES_STORAGE_KEY) ?? '{}',
) as Record<string, unknown>;

describe('useCardSortPreferences', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('migrates legacy settings to Default and clears every override', () => {
    localStorage.setItem(LEGACY_DEFAULT_CARD_SORT_STORAGE_KEY, 'mana_asc');
    localStorage.setItem(LEGACY_CARD_SORT_OVERRIDES_STORAGE_KEY, JSON.stringify({
      gallery: 'name_asc',
      deckBuilder: 'mana_desc',
      deckDetail: 'types_asc',
    }));

    const { defaultSort } = useCardSortPreferences();

    expect(defaultSort.value).toBe('default');
    expect(storedPreferences()).toEqual({
      version: 1,
      defaultSort: 'default',
      overrides: {
        gallery: null,
        deckBuilder: null,
        deckDetail: null,
      },
    });
    expect(localStorage.getItem(LEGACY_DEFAULT_CARD_SORT_STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem(LEGACY_CARD_SORT_OVERRIDES_STORAGE_KEY)).toBeNull();
  });

  test('preserves a valid current-version preference', () => {
    localStorage.setItem(CARD_SORT_PREFERENCES_STORAGE_KEY, JSON.stringify({
      version: 1,
      defaultSort: 'name_asc',
      overrides: {
        gallery: 'mana_desc',
        deckBuilder: null,
        deckDetail: null,
      },
    }));

    const preferences = useCardSortPreferences();
    const gallery = preferences.getOverrideSort('gallery');

    expect(preferences.defaultSort.value).toBe('name_asc');
    expect(gallery.value).toBe('mana_desc');
  });

  test('replaces malformed current storage idempotently', () => {
    localStorage.setItem(CARD_SORT_PREFERENCES_STORAGE_KEY, '{broken');

    expect(migrateCardSortPreferences(localStorage)).toEqual({
      version: 1,
      defaultSort: 'default',
      overrides: {
        gallery: null,
        deckBuilder: null,
        deckDetail: null,
      },
    });
    const firstWrite = localStorage.getItem(CARD_SORT_PREFERENCES_STORAGE_KEY);

    expect(migrateCardSortPreferences(localStorage)).toEqual(JSON.parse(firstWrite ?? '{}'));
    expect(localStorage.getItem(CARD_SORT_PREFERENCES_STORAGE_KEY)).toBe(firstWrite);
  });

  test('falls back in memory when storage is unavailable', () => {
    const unavailableStorage = {
      getItem: () => { throw new Error('unavailable'); },
      setItem: () => { throw new Error('unavailable'); },
      removeItem: () => { throw new Error('unavailable'); },
    };

    expect(migrateCardSortPreferences(unavailableStorage)).toEqual({
      version: 1,
      defaultSort: 'default',
      overrides: {
        gallery: null,
        deckBuilder: null,
        deckDetail: null,
      },
    });
  });

  test('persists later global customization in the versioned record', async () => {
    const { defaultSort } = useCardSortPreferences();
    defaultSort.value = 'mana_asc';
    await nextTick();

    expect(storedPreferences()).toMatchObject({
      version: 1,
      defaultSort: 'mana_asc',
    });
  });

  test('surface override falls back to global default when unset', async () => {
    const { defaultSort } = useCardSortPreferences();
    const gallery = useCardSortSurface('gallery');

    expect(gallery.effectiveSort.value).toBe('default');

    defaultSort.value = 'name_asc';
    await nextTick();

    expect(gallery.overrideSort.value).toBeNull();
    expect(gallery.effectiveSort.value).toBe('name_asc');
  });

  test('surface overrides remain isolated after migration', async () => {
    const deckDetail = useCardSortSurface('deckDetail');
    const gallery = useCardSortSurface('gallery');

    deckDetail.setOverrideSort('name_asc');
    await nextTick();

    expect(deckDetail.overrideSort.value).toBe('name_asc');
    expect(deckDetail.effectiveSort.value).toBe('name_asc');
    expect(gallery.overrideSort.value).toBeNull();
    expect(gallery.effectiveSort.value).toBe('default');

    deckDetail.clearOverrideSort();
    await nextTick();
    expect(deckDetail.effectiveSort.value).toBe('default');
  });
});
