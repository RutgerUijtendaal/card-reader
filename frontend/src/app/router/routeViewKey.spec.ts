import { describe, expect, test } from 'vitest';
import {
  resolveRouteViewKey,
  resolveWorkspaceAwareRouteViewKey,
} from '@/app/router/routeViewKey';

describe('resolveRouteViewKey', () => {
  test('gives each deck editor route a distinct component key', () => {
    expect(resolveRouteViewKey('/my/decks/new')).toBe('deck-editor:/my/decks/new');
    expect(resolveRouteViewKey('/my/decks/deck-1/edit')).toBe(
      'deck-editor:/my/decks/deck-1/edit',
    );
  });

  test('leaves unrelated routes under normal RouterView reuse behavior', () => {
    expect(resolveRouteViewKey('/my/decks')).toBeUndefined();
    expect(resolveRouteViewKey('/playtester/deck-1')).toBeUndefined();
  });

  test('uses workspace generations only for card-pool routes', () => {
    expect(resolveWorkspaceAwareRouteViewKey('/cards', 4, true)).toBe(
      '/cards:workspace:4',
    );
    expect(resolveWorkspaceAwareRouteViewKey('/imports', 4, false)).toBeUndefined();
    expect(resolveWorkspaceAwareRouteViewKey('/my/decks/new', 4, false)).toBe(
      'deck-editor:/my/decks/new',
    );
  });
});
