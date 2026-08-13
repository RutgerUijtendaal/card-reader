import { describe, expect, test } from 'vitest';
import type { ImportJobItem } from '@/features/import-jobs/types';
import {
  formatImportRoles,
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
  classification_inference: {},
  target_card_id: null,
  target_card_version_id: null,
  target_card_pool_snapshot: null,
  target_card_roles_snapshot: [],
  target_card_factions_snapshot: [],
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

  test('renders structured inference and keeps generic warnings safe', () => {
    const evidence = getInferenceEvidence(item({
      resolved_card_roles: ['event', 'location'],
      resolved_card_factions: ['order'],
      classification_inference: {
        roles: {
          mode: 'automatic',
          template_roles: ['location'],
          matched_tag_keys: ['event'],
        },
        factions: {
          mode: 'automatic',
          matched_tag_keys: ['order'],
        },
      },
    }));

    expect(evidence).toContainEqual({ label: 'Template hints', value: 'Location' });
    expect(evidence).toContainEqual({ label: 'Role tags', value: 'event' });
    expect(evidence).toContainEqual({ label: 'Faction tags', value: 'order' });
    expect(getWarningEvidence({ code: 'future_warning', message: 'Future warning.' })).toEqual([]);
  });
});
