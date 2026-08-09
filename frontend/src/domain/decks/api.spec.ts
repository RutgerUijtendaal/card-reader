import { beforeEach, describe, expect, test, vi } from 'vitest';
import { api } from '@/shared/api/client';
import {
  createDeck,
  exportDeckTts,
  fetchDeckRulesMetadata,
  fetchMyDeckByCreationKey,
} from '@/domain/decks/api';
import {
  fallbackDeckBuildingConfigExample,
  fallbackDeckBuildingDefaultConfig,
  fallbackDeckBuildingRules,
} from '@/domain/decks/utils/deckRules';
import type { DeckRulesMetadata } from '@/domain/decks/types';

vi.mock('@/shared/api/client', () => ({
  api: { get: vi.fn(), post: vi.fn() },
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

  test('sends the creation key separately and reports an idempotent replay', async () => {
    const record = { id: 'deck-1', status: { is_valid: true } };
    vi.mocked(api.post).mockResolvedValueOnce({ data: record, status: 200 });
    const payload = {
      name: 'Deck',
      description: null,
      long_description: null,
      difficulty: null,
      visibility: 'private' as const,
      hero_card_id: 'hero-1',
      entries: [],
      sideboards: [],
      tag_ids: [],
      suggested_type_labels: [],
    };

    await expect(createDeck(payload, 'creation-key')).resolves.toEqual({
      record,
      replayed: true,
    });
    expect(api.post).toHaveBeenCalledWith('/my/decks', payload, {
      headers: { 'Idempotency-Key': 'creation-key' },
    });
  });

  test('looks up an owned deck by its creation key', async () => {
    const record = { id: 'deck-1', status: { is_valid: true } };
    vi.mocked(api.get).mockResolvedValueOnce({ data: record });

    await expect(fetchMyDeckByCreationKey('creation-key')).resolves.toEqual({
      status: 'found',
      record,
    });
    expect(api.get).toHaveBeenCalledWith('/my/decks/by-creation-key/creation-key');
  });

  test('distinguishes a deleted creation result from an unused key', async () => {
    vi.mocked(api.get)
      .mockRejectedValueOnce({ isAxiosError: true, response: { status: 410 } })
      .mockRejectedValueOnce({ isAxiosError: true, response: { status: 404 } });

    await expect(fetchMyDeckByCreationKey('deleted-key')).resolves.toEqual({
      status: 'deleted',
    });
    await expect(fetchMyDeckByCreationKey('missing-key')).resolves.toEqual({
      status: 'missing',
    });
  });
});
