import { describe, expect, test } from 'vitest';
import { buildHeroAffinityManaPreset, getManaSymbolKeysForAffinityKeys } from '@/composables/decks/affinityMana';
import type { SymbolFilterOption } from '@/modules/card-detail/types';
import type { DeckCardSummary } from '@/modules/decks/types';

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
  id: `${key}-id`,
  key,
  label: key,
  linked_card_count: 1,
  symbol_type: 'mana',
  text_token: `{${key}}`,
  asset_url: null,
});

describe('affinity mana mapping', () => {
  test('maps standardized affinity keys to mana keys', () => {
    expect(getManaSymbolKeysForAffinityKeys(['martial-affinity', 'arcane-affinity', 'martial-affinity'])).toEqual([
      'arcane-mana',
      'martial-mana',
    ]);
  });

  test('builds an include/exclude mana preset from hero affinity symbols', () => {
    const hero = {
      symbols: [symbol('martial-affinity', 'affinity'), symbol('divine-affinity', 'affinity'), symbol('exhaust', 'generic')],
    };

    expect(
      buildHeroAffinityManaPreset(hero, [
        manaOption('arcane-mana'),
        manaOption('divine-mana'),
        manaOption('martial-mana'),
        manaOption('occult-mana'),
      ]),
    ).toEqual({
      includedManaSymbolKeys: ['divine-mana', 'martial-mana'],
      excludedManaSymbolKeys: ['arcane-mana', 'occult-mana'],
    });
  });

  test('does not create a preset when the hero has no mapped affinity', () => {
    expect(buildHeroAffinityManaPreset({ symbols: [symbol('sola-affinity', 'affinity')] }, [manaOption('martial-mana')])).toBeNull();
  });
});
