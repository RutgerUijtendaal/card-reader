import { beforeEach, describe, expect, test } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import {
  buildWorkspaceGalleryLocation,
  normalizeAccessibleCardPools,
  resolveCardPoolWorkspace,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

describe('card pool workspace', () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
  });

  test('normalizes accessible pools into canonical order with Player available', () => {
    expect(normalizeAccessibleCardPools(['neutral', 'evil'])).toEqual([
      'player',
      'evil',
      'neutral',
    ]);
  });

  test('prefers an accessible route pool, then a permitted preference, then Player', () => {
    expect(resolveCardPoolWorkspace(['player', 'evil'], 'evil', 'player')).toBe('evil');
    expect(resolveCardPoolWorkspace(['player', 'evil'], undefined, 'evil')).toBe('evil');
    expect(resolveCardPoolWorkspace(['player'], 'evil', 'neutral')).toBe('player');
  });

  test('falls back synchronously and advances the generation when access is lost', () => {
    const workspace = useCardPoolWorkspaceStore();
    workspace.synchronizeSession(['player', 'evil', 'neutral'], 'staff:1', 'evil');
    const restrictedGeneration = workspace.generation;

    const changed = workspace.synchronizeSession(['player'], 'user:1');

    expect(changed).toBe(true);
    expect(workspace.activePool).toBe('player');
    expect(workspace.generation).toBeGreaterThan(restrictedGeneration);
  });

  test('advances the generation when session identity changes without a pool change', () => {
    const workspace = useCardPoolWorkspaceStore();
    workspace.synchronizeSession(['player'], 'anonymous');
    const anonymousGeneration = workspace.generation;

    workspace.synchronizeSession(['player'], 'user:7');

    expect(workspace.activePool).toBe('player');
    expect(workspace.generation).toBeGreaterThan(anonymousGeneration);
  });

  test('builds a shareable gallery location without serializing the Player default', () => {
    expect(buildWorkspaceGalleryLocation('player')).toBe('/cards');
    expect(buildWorkspaceGalleryLocation('evil')).toEqual({
      path: '/cards',
      query: { card_pool: 'evil' },
    });
  });

});
