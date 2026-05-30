import { describe, expect, test, vi } from 'vitest';
import { api } from '@/api/client';
import {
  fallbackDeckBuildingConfigExample,
  fallbackDeckBuildingDefaultConfig,
  fallbackDeckBuildingRules,
  fetchDeckRulesMetadata,
  formatDeckBuildingConfigJson,
  type DeckRulesMetadata,
} from '@/modules/decks/deckRules';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const backendMetadataFixture: DeckRulesMetadata = {
  supported_rule_ids: [
    'mainboard_copy_limit',
    'mainboard_card_count',
    'mana_type_count',
    'legendary_copy_limit',
    'sideboard_entry_quantity',
  ],
  allowed_severities: ['hard', 'soft'],
  allowed_scopes: ['mainboard', 'whole_deck'],
  default_config: fallbackDeckBuildingDefaultConfig,
  default_rules: fallbackDeckBuildingRules(),
  example_config: fallbackDeckBuildingConfigExample,
};

describe('deckRules', () => {
  test('loads backend metadata from the deck rules endpoint', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: backendMetadataFixture });

    await expect(fetchDeckRulesMetadata()).resolves.toEqual(backendMetadataFixture);
    expect(api.get).toHaveBeenCalledWith('/decks/rules');
  });

  test('keeps frontend fallback rule assumptions aligned with backend metadata shape', () => {
    const fallbackRules = fallbackDeckBuildingRules();

    expect(Object.keys(fallbackRules).sort()).toEqual(
      backendMetadataFixture.supported_rule_ids.slice().sort(),
    );
    expect(fallbackRules.mainboard_copy_limit.max).toBe(4);
    expect(fallbackRules.mana_type_count.min).toBe(3);
    expect(fallbackRules.legendary_copy_limit.severity).toBe('soft');
    expect(fallbackRules.legendary_copy_limit.scope).toBe('mainboard');
    expect(formatDeckBuildingConfigJson(fallbackDeckBuildingDefaultConfig)).toContain('overrides');
    expect(formatDeckBuildingConfigJson(fallbackDeckBuildingConfigExample)).toContain(
      'mainboard_copy_limit',
    );
  });
});
