import { beforeEach, describe, expect, test } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { nextTick } from 'vue';
import {
  buildWorkspaceGalleryLocation,
  CARD_POOL_WORKSPACE_PREFERENCE_KEY,
  resolveCardPoolWorkspace,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

describe('card pool workspace', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  test('prefers a valid saved preference, then Player', () => {
    expect(resolveCardPoolWorkspace('evil')).toBe('evil');
    expect(resolveCardPoolWorkspace('unsupported')).toBe('player');
  });

  test('makes every pool available and persists selections', async () => {
    const workspace = useCardPoolWorkspaceStore();
    expect(workspace.availableOptions.map((option) => option.value)).toEqual([
      'player',
      'evil',
      'neutral',
    ]);

    expect(workspace.selectPool('evil')).toBe(true);
    await nextTick();

    expect(workspace.activePool).toBe('evil');
    expect(workspace.generation).toBe(1);
    expect(localStorage.getItem(CARD_POOL_WORKSPACE_PREFERENCE_KEY)).toBe('evil');
    expect(workspace.selectPool('evil')).toBe(false);
    expect(workspace.generation).toBe(1);
  });

  test('builds a shareable gallery location without serializing the Player default', () => {
    expect(buildWorkspaceGalleryLocation('player')).toBe('/cards');
    expect(buildWorkspaceGalleryLocation('evil')).toEqual({
      path: '/cards',
      query: { card_pool: 'evil' },
    });
  });
});
