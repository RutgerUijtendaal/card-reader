import { describe, expect, test } from 'vitest';
import { buildHeroManaFamilyPreset } from '@/domain/decks/utils/heroManaFamilies';
import type { SymbolFilterOption } from '@/domain/cards/types';

const manaOption = (key: string): SymbolFilterOption => ({
  id: key,
  key,
  label: key,
  linked_card_count: 1,
  symbol_type: 'mana_family',
  text_token: `{${key}}`,
  asset_url: null,
});

describe('hero mana-family presets', () => {
  test('builds an include/exclude mana preset from stored hero families', () => {
    const hero = {
      card_mana_families: ['martial', 'divine'] as Array<'martial' | 'divine'>,
    };

    expect(
      buildHeroManaFamilyPreset(hero, [
        manaOption('arcane'),
        manaOption('divine'),
        manaOption('martial'),
        manaOption('occult'),
      ]),
    ).toEqual({
      includedManaFamilyKeys: ['divine', 'martial'],
      excludedManaFamilyKeys: ['arcane', 'occult'],
    });
  });

  test('does not create a preset when the hero has no stored mana family', () => {
    expect(buildHeroManaFamilyPreset(
      { card_mana_families: [] },
      [manaOption('martial')],
    )).toBeNull();
  });
});
