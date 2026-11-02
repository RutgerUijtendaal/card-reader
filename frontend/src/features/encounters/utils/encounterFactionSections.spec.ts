import { describe, expect, test } from 'vitest';
import type { EncounterSummary } from '@/domain/encounters/types';
import { groupEncountersByFaction } from './encounterFactionSections';

const encounter = (id: string, factions: string[]): EncounterSummary =>
  ({ id, factions }) as unknown as EncounterSummary;

describe('groupEncountersByFaction', () => {
  test('orders single factions canonically, then mixed, then none', () => {
    const sections = groupEncountersByFaction([
      encounter('none', []),
      encounter('fire', ['fire']),
      encounter('mixed', ['order', 'blood']),
      encounter('order-1', ['order']),
      encounter('order-2', ['order']),
    ]);

    expect(sections.map((section) => section.label)).toEqual([
      'Order',
      'Fire',
      'Multiple factions',
      'No faction',
    ]);
    expect(sections[0].encounters.map((record) => record.id)).toEqual(['order-1', 'order-2']);
  });

  test('returns no sections for an empty list', () => {
    expect(groupEncountersByFaction([])).toEqual([]);
  });
});
