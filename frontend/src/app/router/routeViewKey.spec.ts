import { describe, expect, test } from 'vitest';
import { resolveRouteViewKey } from '@/app/router/routeViewKey';

describe('resolveRouteViewKey', () => {
  test('gives each deck editor route a distinct component key', () => {
    expect(resolveRouteViewKey('/my/decks/new', 0)).toBe('deck-editor:/my/decks/new');
    expect(resolveRouteViewKey('/my/decks/deck-1/edit', 0)).toBe(
      'deck-editor:/my/decks/deck-1/edit',
    );
  });

  test('leaves unrelated routes under normal RouterView reuse behavior', () => {
    expect(resolveRouteViewKey('/my/decks', 0)).toBeUndefined();
    expect(resolveRouteViewKey('/playtester/deck-1', 0)).toBeUndefined();
  });

  test('only keys scope-dependent routes by workspace context', () => {
    expect(resolveRouteViewKey('/cards', 3)).toBeUndefined();
    expect(resolveRouteViewKey('/imports', 3)).toBeUndefined();
    expect(resolveRouteViewKey('/notifications', 3)).toBe('notifications:workspace-3');
    expect(resolveRouteViewKey('/notifications', 4)).toBe('notifications:workspace-4');
    expect(resolveRouteViewKey('/my/decks/new', 3)).toBe('deck-editor:/my/decks/new');
  });
});
