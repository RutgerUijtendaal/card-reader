import { describe, expect, test } from 'vitest';
import { resolveRouteViewKey } from '@/app/router/routeViewKey';

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
});
