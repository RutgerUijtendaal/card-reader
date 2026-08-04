import { describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import { fetchDeckRulesMetadata } from '@/domain/decks/api';
import {
  fallbackDeckBuildingConfigExample,
  fallbackDeckBuildingDefaultConfig,
  fallbackDeckBuildingRules,
} from '@/domain/decks/utils/deckRules';
import type { DeckRulesMetadata } from '@/domain/decks/types';

vi.mock('@/shared/api/client', () => ({
  api: { get: vi.fn() },
}));

describe('deck API', () => {
  test('loads backend metadata from the deck rules endpoint', async () => {
    const metadata: DeckRulesMetadata = {
      supported_rule_ids: ['mainboard_copy_limit'],
      allowed_severities: ['hard', 'soft'],
      allowed_scopes: ['mainboard', 'whole_deck'],
      allowed_applications: ['deck', 'self'],
      default_config: fallbackDeckBuildingDefaultConfig,
      default_rules: fallbackDeckBuildingRules(),
      example_config: fallbackDeckBuildingConfigExample,
    };
    vi.mocked(api.get).mockResolvedValueOnce({ data: metadata });

    await expect(fetchDeckRulesMetadata()).resolves.toEqual(metadata);
    expect(api.get).toHaveBeenCalledWith('/decks/rules');
  });
});
