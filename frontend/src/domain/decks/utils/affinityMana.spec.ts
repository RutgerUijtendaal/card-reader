import { describe, expect, test } from 'vitest';
import { buildHeroAffinityManaPreset, getManaSymbolKeysForAffinityKeys } from '@/domain/decks/utils/affinityMana';
import type { SymbolFilterOption } from '@/domain/cards/types';
import type { DeckCardSummary } from '@/domain/decks/types';

const symbol = (key: string, symbolType: string): DeckCardSummary['symbols'][number] => ({
  id: `${key}-id`,
  key,
  label: key,
  linked_card_count: 1,
  symbol_type: symbolType,
  text_token: `{${key}}`,
  asset_url: null,
});

const manaOption = (key: string): SymbolFilterOption => ({
  id: key,
  key,
  label: key,
  linked_card_count: 1,
  symbol_type: 'mana',
  text_token: `{${key}}`,
  asset_url: null,
});

const familyBySymbolKey = {
  'arcane-affinity': 'arcane',
  'divine-affinity': 'divine',
  'martial-affinity': 'martial',
  'martial-mana': 'martial',
};

describe('affinity mana mapping', () => {
  test('maps standardized affinity keys to mana keys', () => {
    expect(getManaSymbolKeysForAffinityKeys(
      ['martial-affinity', 'arcane-affinity', 'martial-affinity'],
      familyBySymbolKey,
    )).toEqual([
      'arcane',
      'martial',
    ]);
  });

  test('builds an include/exclude mana preset from either hero representation', () => {
    const hero = {
      symbols: [symbol('martial-mana', 'mana'), symbol('divine-affinity', 'affinity'), symbol('exhaust', 'generic')],
    };

    expect(
      buildHeroAffinityManaPreset(hero, [
        manaOption('arcane'),
        manaOption('divine'),
        manaOption('martial'),
        manaOption('occult'),
      ], familyBySymbolKey),
    ).toEqual({
      includedManaSymbolKeys: ['divine', 'martial'],
      excludedManaSymbolKeys: ['arcane', 'occult'],
    });
  });

  test('does not create a preset when the hero has no mapped affinity', () => {
    expect(buildHeroAffinityManaPreset(
      { symbols: [symbol('sola-affinity', 'affinity')] },
      [manaOption('martial')],
      familyBySymbolKey,
    )).toBeNull();
  });
});
