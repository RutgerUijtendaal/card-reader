import { describe, expect, test } from 'vitest';
import {
  GALLERY_VISIBLE_FILTER_SECTIONS,
  sanitizeGalleryFilterStateForPool,
} from '@/domain/cards/utils/filters/cardGalleryFacetPolicy';
import { createEmptyCardFilterState } from '@/domain/cards/utils/filters/cardFilterState';
import {
  buildCardFilterRouteQuery,
  parseCardFilterRouteQuery,
} from '@/domain/cards/utils/filters/cardFilterRouteState';
import { buildCardFilterSelectionState } from '@/domain/cards/utils/filters/cardFilterSelection';
import { buildCardFilterApiPayload } from '@/domain/cards/utils/filters/cardFilterRequest';

const EMPTY_CATALOG = {
  keywords: [],
  tags: [],
  types: [],
  manaSymbols: [],
  affinitySymbols: [],
  allAffinitySymbols: [],
  devotionSymbols: [],
  otherSymbols: [],
  manaFamilyBySymbolKey: {},
};

const populatedState = () => ({
  ...createEmptyCardFilterState(),
  query: 'dragon',
  cardRoleMatch: 'all' as const,
  cardRoleKeys: ['boss' as const],
  cardRoleExcludeKeys: ['event' as const],
  cardFactionMatch: 'all' as const,
  cardFactionKeys: ['blood' as const],
  cardFactionExcludeKeys: ['order' as const],
  manaSymbolMatch: 'all' as const,
  manaSymbolKeys: ['dark'],
  manaSymbolExcludeKeys: ['primal'],
  manaCostMin: '2',
  manaCostMax: '5',
  affinitySymbolMatch: 'all' as const,
  affinitySymbolKeys: ['dark-affinity'],
  affinitySymbolExcludeKeys: ['primal-affinity'],
  devotionSymbolMatch: 'all' as const,
  devotionSymbolKeys: ['blood-devotion'],
  devotionSymbolExcludeKeys: ['order-devotion'],
  otherSymbolMatch: 'all' as const,
  otherSymbolKeys: ['legendary'],
  attackMin: '3',
  tagKeys: ['dragon'],
});

describe('cardGalleryFacetPolicy', () => {
  test('defines the exact Player, Evil, and Neutral Gallery facet matrix', () => {
    expect(GALLERY_VISIBLE_FILTER_SECTIONS).toEqual({
      player: ['mana', 'types', 'affinity', 'devotion', 'generic', 'keywords', 'tags'],
      evil: ['factions', 'types', 'generic', 'keywords', 'tags'],
      neutral: ['types', 'generic', 'keywords', 'tags'],
    });

    Object.values(GALLERY_VISIBLE_FILTER_SECTIONS).forEach((sections) => {
      expect(sections).not.toContain('roles');
    });
  });

  test('keeps Player mana, affinity, and devotion while clearing roles and factions', () => {
    const sanitized = sanitizeGalleryFilterStateForPool(populatedState(), 'player');

    expect(sanitized).toMatchObject({
      cardPool: 'player',
      cardRoleMatch: 'any',
      cardRoleKeys: [],
      cardRoleExcludeKeys: [],
      cardFactionMatch: 'any',
      cardFactionKeys: [],
      cardFactionExcludeKeys: [],
      manaSymbolMatch: 'all',
      manaSymbolKeys: ['dark'],
      manaSymbolExcludeKeys: ['primal'],
      manaCostMin: '2',
      manaCostMax: '5',
      affinitySymbolKeys: ['dark-affinity'],
      devotionSymbolKeys: ['blood-devotion'],
      otherSymbolKeys: ['legendary'],
      attackMin: '3',
      tagKeys: ['dragon'],
    });
  });

  test('keeps Evil factions while clearing mana, affinity, devotion, and arbitrary roles', () => {
    const sanitized = sanitizeGalleryFilterStateForPool(populatedState(), 'evil');

    expect(sanitized).toMatchObject({
      cardPool: 'evil',
      cardRoleMatch: 'any',
      cardRoleKeys: [],
      cardRoleExcludeKeys: [],
      cardFactionMatch: 'all',
      cardFactionKeys: ['blood'],
      cardFactionExcludeKeys: ['order'],
      manaSymbolMatch: 'any',
      manaSymbolKeys: [],
      manaSymbolExcludeKeys: [],
      manaCostMin: '',
      manaCostMax: '',
      affinitySymbolMatch: 'any',
      affinitySymbolKeys: [],
      affinitySymbolExcludeKeys: [],
      devotionSymbolMatch: 'any',
      devotionSymbolKeys: [],
      devotionSymbolExcludeKeys: [],
      otherSymbolKeys: ['legendary'],
      attackMin: '3',
      tagKeys: ['dragon'],
    });
  });

  test('clears every pool-specific facet for Neutral and is deterministic and idempotent', () => {
    const sanitized = sanitizeGalleryFilterStateForPool(populatedState(), 'neutral');

    expect(sanitized).toMatchObject({
      cardPool: 'neutral',
      cardRoleMatch: 'any',
      cardRoleKeys: [],
      cardRoleExcludeKeys: [],
      cardFactionMatch: 'any',
      cardFactionKeys: [],
      cardFactionExcludeKeys: [],
      manaSymbolMatch: 'any',
      manaSymbolKeys: [],
      manaSymbolExcludeKeys: [],
      manaCostMin: '',
      manaCostMax: '',
      affinitySymbolKeys: [],
      affinitySymbolExcludeKeys: [],
      devotionSymbolKeys: [],
      devotionSymbolExcludeKeys: [],
      otherSymbolKeys: ['legendary'],
      attackMin: '3',
      tagKeys: ['dragon'],
    });
    expect(sanitizeGalleryFilterStateForPool(sanitized, 'neutral')).toEqual(sanitized);
    expect(sanitizeGalleryFilterStateForPool(populatedState(), 'neutral')).toEqual(sanitized);
  });

  test('removes hidden direct-route values before canonical routes and requests are built', () => {
    const directRouteState = parseCardFilterRouteQuery({
      q: 'dragon',
      card_pool: 'evil',
      card_roles: 'boss',
      card_role_exclude: 'event',
      card_role_match: 'all',
      card_factions: 'blood',
      card_faction_match: 'all',
      mana_family_keys: 'dark',
      mana_family_match: 'all',
      mana_cost_min: '2',
      affinity_symbol_keys: 'dark-affinity',
      affinity_symbol_match: 'all',
      devotion_symbol_keys: 'blood-devotion',
      devotion_symbol_match: 'all',
      tag_keys: 'dragon',
    });
    const sanitized = sanitizeGalleryFilterStateForPool(directRouteState, 'evil');
    const routeQuery = buildCardFilterRouteQuery(sanitized);
    const request = buildCardFilterApiPayload(
      buildCardFilterSelectionState(sanitized, EMPTY_CATALOG),
    );

    expect(routeQuery).toEqual({
      q: 'dragon',
      card_pool: 'evil',
      card_factions: ['blood'],
      card_faction_match: 'all',
      tag_keys: ['dragon'],
    });
    expect(request).toMatchObject({
      q: 'dragon',
      card_pool: 'evil',
      card_factions: ['blood'],
      card_faction_match: 'all',
    });
    expect(request).not.toHaveProperty('card_roles');
    expect(request).not.toHaveProperty('card_role_exclude');
    expect(request).not.toHaveProperty('mana_family_keys');
    expect(request).not.toHaveProperty('mana_cost_min');
    expect(request).not.toHaveProperty('affinity_symbol_ids');
    expect(request).not.toHaveProperty('devotion_symbol_ids');
  });
});
