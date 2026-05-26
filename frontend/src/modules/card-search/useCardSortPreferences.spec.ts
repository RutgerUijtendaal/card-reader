import { beforeEach, describe, expect, test } from 'vitest';
import { nextTick } from 'vue';
import { useCardSortPreferences, useCardSortSurface } from '@/modules/card-search/useCardSortPreferences';

describe('useCardSortPreferences', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('defaults to recently updated', () => {
    const { defaultSort } = useCardSortPreferences();

    expect(defaultSort.value).toBe('updated_desc');
  });

  test('persists the global default sort', async () => {
    const { defaultSort } = useCardSortPreferences();
    defaultSort.value = 'mana_asc';
    await nextTick();

    expect(localStorage.getItem('card-reader.default-card-sort')).toBe('mana_asc');
  });

  test('surface override falls back to global default when unset', async () => {
    const { defaultSort } = useCardSortPreferences();
    const gallery = useCardSortSurface('gallery');

    expect(gallery.effectiveSort.value).toBe('updated_desc');

    defaultSort.value = 'name_asc';
    await nextTick();

    expect(gallery.overrideSort.value).toBeNull();
    expect(gallery.effectiveSort.value).toBe('name_asc');
  });

  test('surface override does not rewrite the global default', async () => {
    const { defaultSort } = useCardSortPreferences();
    const deckBuilder = useCardSortSurface('deckBuilder');

    defaultSort.value = 'updated_desc';
    deckBuilder.setOverrideSort('mana_desc');
    await nextTick();

    expect(defaultSort.value).toBe('updated_desc');
    expect(deckBuilder.overrideSort.value).toBe('mana_desc');
    expect(deckBuilder.effectiveSort.value).toBe('mana_desc');

    deckBuilder.clearOverrideSort();
    await nextTick();

    expect(deckBuilder.overrideSort.value).toBeNull();
    expect(deckBuilder.effectiveSort.value).toBe('updated_desc');
  });

  test('deck detail sort override is isolated from other surfaces', async () => {
    const deckDetail = useCardSortSurface('deckDetail');
    const gallery = useCardSortSurface('gallery');

    deckDetail.setOverrideSort('name_asc');
    await nextTick();

    expect(deckDetail.overrideSort.value).toBe('name_asc');
    expect(deckDetail.effectiveSort.value).toBe('name_asc');
    expect(gallery.overrideSort.value).toBeNull();
    expect(gallery.effectiveSort.value).toBe('updated_desc');
  });
});
