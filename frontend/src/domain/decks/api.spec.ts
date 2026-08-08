import { beforeEach, describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import { exportDeckTts, fetchDeckRulesMetadata } from '@/domain/decks/api';
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  test('maps the structured TTS deck export response', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        encoded_payload: 'encoded-deck',
        exported_count: 61,
        skipped_count: 4,
        sheet_count: 2,
      },
    });

    await expect(exportDeckTts('deck-1', 'sideboard-1')).resolves.toEqual({
      encodedPayload: 'encoded-deck',
      exportedCount: 61,
      skippedCount: 4,
      sheetCount: 2,
    });
    expect(api.get).toHaveBeenCalledWith('/decks/deck-1/exports/tts', {
      params: { sideboard_id: 'sideboard-1' },
    });
  });
});
