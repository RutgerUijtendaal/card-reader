import { describe, expect, test } from 'vitest';
import type { ImportJobItem } from '@/features/import-jobs/types';
import {
  formatImportFactions,
  formatImportManaFamilies,
  formatImportRoles,
  formatResolvedImportManaFamilies,
  getImportEvidenceState,
  getInferenceEvidence,
  getWarningEvidence,
} from '@/features/import-jobs/utils/importEvidence';

const item = (overrides: Partial<ImportJobItem> = {}): ImportJobItem => ({
  id: 'item',
  source_file: 'card.webp',
  status: 'queued',
  error_message: null,
  warning_code: null,
  warning_message: null,
  warnings: [],
  resolved_card_roles: [],
  resolved_card_factions: [],
  resolved_card_mana_families: [],
  classification_inference: {},
  target_card_id: null,
  target_card_version_id: null,
  target_card_pool_snapshot: null,
  target_card_roles_snapshot: [],
  target_card_factions_snapshot: [],
  target_card_mana_families_snapshot: [],
  card_tab_url: null,
  ...overrides,
});

describe('import evidence presentation', () => {
  test('distinguishes pending, unavailable, resolved, and warning states', () => {
    expect(getImportEvidenceState(item())).toBe('pending');
    expect(getImportEvidenceState(item({ status: 'failed' }))).toBe('unavailable');
    expect(getImportEvidenceState(item({
      status: 'completed',
      classification_inference: { roles: { mode: 'automatic' } },
    }))).toBe('resolved');
    expect(getImportEvidenceState(item({
      status: 'completed',
      classification_inference: { roles: { mode: 'automatic' } },
      warnings: [{ code: 'future_warning', message: 'Future warning.' }],
    }))).toBe('resolved_with_warning');
  });

  test('uses the shared role registry for Normal and multi-role labels', () => {
    expect(formatImportRoles([])).toBe('Normal');
    expect(formatImportRoles(['hero', 'location'])).toBe('Hero, Location');
    expect(formatImportRoles(['unknown', 'boon'])).toBe('Boon');
  });

  test('uses the shared faction registry for Dark and Metal labels', () => {
    expect(formatImportFactions([])).toBe('No faction');
    expect(formatImportFactions(['dark', 'metal'])).toBe('Dark, Metal');
  });

  test('distinguishes explicit Colorless from unavailable legacy mana evidence', () => {
    expect(formatImportManaFamilies([])).toBe('Colorless');
    expect(formatImportManaFamilies(undefined)).toBe('Unavailable');
    expect(formatResolvedImportManaFamilies(item({
      status: 'completed',
      resolved_card_mana_families: [],
      classification_inference: { roles: { mode: 'automatic' } },
    }))).toBe('Unavailable');
    expect(formatResolvedImportManaFamilies(item({
      status: 'completed',
      resolved_card_mana_families: [],
      classification_inference: { mana_families: { mode: 'automatic' } },
    }))).toBe('Colorless');
  });

  test('renders structured inference and keeps generic warnings safe', () => {
    const evidence = getInferenceEvidence(item({
      resolved_card_roles: ['event', 'location'],
      resolved_card_factions: ['order'],
      resolved_card_mana_families: ['arcane'],
      classification_inference: {
        roles: {
          mode: 'automatic',
          matched_tag_sources: [{ id: 'tag-event', key: 'event' }],
          matched_type_sources: [{ id: 'type-location', key: 'location' }],
          matched_symbol_sources: [{ id: 'symbol-hero', key: 'hero-crown' }],
        },
        factions: {
          mode: 'automatic',
          matched_tag_sources: [{ id: 'tag-order', key: 'order' }],
          matched_symbol_sources: [{ id: 'symbol-order', key: 'order-crest' }],
        },
        mana_families: {
          mode: 'automatic',
          matched_symbol_sources: [{ id: 'symbol-arcane', key: 'arcane-mana' }],
        },
      },
    }));

    expect(evidence).toContainEqual({ label: 'Role tags', value: 'event' });
    expect(evidence).toContainEqual({ label: 'Role types', value: 'location' });
    expect(evidence).toContainEqual({ label: 'Role symbols', value: 'hero-crown' });
    expect(evidence).toContainEqual({ label: 'Faction tags', value: 'order' });
    expect(evidence).toContainEqual({ label: 'Faction symbols', value: 'order-crest' });
    expect(evidence).toContainEqual({ label: 'Mana symbols', value: 'arcane-mana' });
    expect(getWarningEvidence({ code: 'future_warning', message: 'Future warning.' })).toEqual([]);
  });

  test('renders unknown Evil faction match evidence without exposing candidates', () => {
    expect(getWarningEvidence({
      code: 'evil_faction_unresolved',
      message: 'Review the Card faction.',
      details: {
        reason: 'conflicting_evidence',
        checksum_candidate_count: 1,
        name_candidate_count: 1,
      },
    })).toEqual([
      { label: 'Match result', value: 'Image and name disagree' },
      { label: 'Image candidates', value: '1' },
      { label: 'Name candidates', value: '1' },
    ]);
  });

  test('labels historical missing facet evidence as unavailable', () => {
    const evidence = getInferenceEvidence(item({
      status: 'completed',
      classification_inference: {
        roles: { mode: 'automatic', matched_tag_sources: [{ id: 'tag-hero', key: 'hero' }] },
        factions: {},
      },
    }));

    expect(evidence).toContainEqual({ label: 'Role resolution', value: 'Automatic' });
    expect(evidence).toContainEqual({ label: 'Faction resolution', value: 'Unavailable' });
    expect(evidence).toContainEqual({ label: 'Mana resolution', value: 'Unavailable' });
    expect(evidence).not.toContainEqual({ label: 'Faction signals', value: 'None matched' });
  });
});
