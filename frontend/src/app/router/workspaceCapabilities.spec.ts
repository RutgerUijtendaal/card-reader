import { describe, expect, test } from 'vitest';
import type { LocationQuery, RouteMeta } from 'vue-router';
import {
  resolveWorkspaceSelectionDecision,
  type WorkspaceRouteCapability,
} from '@/app/router/workspaceCapabilities';

const route = (
  workspaceCapability: WorkspaceRouteCapability,
  path = '/settings',
  query: LocationQuery = {},
) => ({
  path,
  query,
  hash: '',
  meta: { workspaceCapability } satisfies RouteMeta,
});

describe('workspace route capabilities', () => {
  test('keeps global routes in place', () => {
    expect(
      resolveWorkspaceSelectionDecision(
        route('global'),
        'evil',
        'player',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({ kind: 'stay' });
  });

  test('replaces Gallery filters with the canonical target workspace', () => {
    expect(
      resolveWorkspaceSelectionDecision(
        route('gallery', '/cards', { q: 'hero', card_pool: 'evil' }),
        'neutral',
        'evil',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({
      kind: 'replace-gallery',
      location: { path: '/cards', query: { card_pool: 'neutral' } },
      navigation: 'replace',
    });
    expect(
      resolveWorkspaceSelectionDecision(
        route('gallery', '/cards', { q: 'hero', card_pool: 'evil' }),
        'player',
        'evil',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({
      kind: 'replace-gallery',
      location: { path: '/cards', query: { card_pool: 'player' } },
      navigation: 'replace',
    });
    expect(
      resolveWorkspaceSelectionDecision(
        route('gallery', '/cards', { card_pool: 'evil' }),
        'player',
        'player',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({
      kind: 'replace-gallery',
      location: { path: '/cards', query: { card_pool: 'player' } },
      navigation: 'replace',
    });
  });

  test('keeps resource identity and rewrites only its workspace return context', () => {
    expect(
      resolveWorkspaceSelectionDecision(
        route('resource', '/cards/card-1/edit', {
          card_pool: 'evil',
          return_card_pool: 'player',
          tab: 'card-version',
        }),
        'neutral',
        'player',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({
      kind: 'update-resource-context',
      location: {
        path: '/cards/card-1/edit',
        query: {
          card_pool: 'evil',
          return_card_pool: 'neutral',
          tab: 'card-version',
        },
        hash: '',
      },
      navigation: 'replace',
    });
  });

  test('falls back from Player-only routes only for restricted workspaces', () => {
    expect(
      resolveWorkspaceSelectionDecision(
        route('player-only', '/playtester/deck-1'),
        'evil',
        'player',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({
      kind: 'fallback-gallery',
      location: { path: '/cards', query: { card_pool: 'evil' } },
      navigation: 'push',
    });
    expect(
      resolveWorkspaceSelectionDecision(
        route('player-only', '/playtester/deck-1'),
        'player',
        'player',
        ['player', 'evil', 'neutral'],
      ),
    ).toEqual({ kind: 'stay' });
  });

  test('rejects inaccessible workspaces and undeclared routes', () => {
    expect(
      resolveWorkspaceSelectionDecision(
        route('global'),
        'evil',
        'player',
        ['player'],
      ),
    ).toEqual({ kind: 'reject' });
    expect(
      resolveWorkspaceSelectionDecision(
        { path: '/unknown', query: {}, hash: '', meta: {} },
        'evil',
        'player',
        ['player', 'evil'],
      ),
    ).toEqual({ kind: 'reject' });
  });
});
