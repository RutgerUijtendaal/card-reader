import { describe, expect, test } from 'vitest';
import {
  fallbackDeckBuildingConfigExample,
  fallbackDeckBuildingDefaultConfig,
  fallbackDeckBuildingRules,
  formatDeckBuildingConfigJson,
} from '@/domain/decks/utils/deckRules';
const supportedRuleIds = [
    'mainboard_copy_limit',
    'mainboard_card_count',
    'mana_type_count',
    'legendary_copy_limit',
    'sideboard_entry_quantity',
] as const;

describe('deckRules', () => {
  test('keeps frontend fallback rule assumptions aligned with backend metadata shape', () => {
    const fallbackRules = fallbackDeckBuildingRules();

    expect(Object.keys(fallbackRules).sort()).toEqual(
      supportedRuleIds.slice().sort(),
    );
    expect(fallbackRules.mainboard_copy_limit.max).toBe(4);
    expect(fallbackRules.mana_type_count.min).toBe(3);
    expect(fallbackRules.legendary_copy_limit.severity).toBe('soft');
    expect(fallbackRules.legendary_copy_limit.scope).toBe('mainboard');
    expect(formatDeckBuildingConfigJson(fallbackDeckBuildingDefaultConfig)).toContain('overrides');
    expect(formatDeckBuildingConfigJson(fallbackDeckBuildingConfigExample)).toContain(
      'mainboard_copy_limit',
    );
    expect(formatDeckBuildingConfigJson(fallbackDeckBuildingConfigExample)).toContain(
      'applies_to',
    );
  });
});
