import { describe, expect, test } from 'vitest';
import type { CardFilterSelectionState } from './cardFilterState';
import { buildCardFilterApiPayload, buildCardFilterApiSearchParams } from './cardFilterRequest';

const selection: CardFilterSelectionState = {
  query: '',
  lifecycleStatus: 'deprecated',
  keywordMatch: 'all',
  tagMatch: 'all',
  typeMatch: 'any',
  manaSymbolMatch: 'all',
  affinitySymbolMatch: 'all',
  devotionSymbolMatch: 'any',
  otherSymbolMatch: 'any',
  templateId: '',
  manaCostMin: '2',
  manaCostMax: '7',
  attackMin: '',
  attackMax: '',
  healthMin: '',
  healthMax: '',
  keywordIds: ['kw-1'],
  tagIds: ['tag-1'],
  manaTypeSymbolIds: ['arcane'],
  manaTypeSymbolExcludeIds: ['arcane'],
  affinitySymbolIds: ['sym-2'],
  affinitySymbolExcludeIds: ['sym-2'],
  devotionSymbolIds: ['sym-3'],
  devotionSymbolExcludeIds: ['sym-3'],
  otherSymbolIds: ['sym-4'],
  otherSymbolExcludeIds: ['sym-4'],
  typeIds: ['type-1'],
  typeExcludeIds: ['type-2'],
};

describe('cardFilterRequest', () => {
  test('builds API params and payloads with UUID ids only', () => {
    const params = buildCardFilterApiSearchParams(selection);
    const payload = buildCardFilterApiPayload(selection);

    expect(params.get('lifecycle_status')).toBe('deprecated');
    expect(params.getAll('keyword_ids')).toEqual(['kw-1']);
    expect(params.get('keyword_match')).toBe('all');
    expect(params.getAll('tag_ids')).toEqual(['tag-1']);
    expect(params.get('tag_match')).toBe('all');
    expect(params.getAll('mana_family_keys')).toEqual(['arcane']);
    expect(params.getAll('mana_family_exclude_keys')).toEqual(['arcane']);
    expect(params.get('mana_family_match')).toBe('all');
    expect(params.getAll('affinity_symbol_ids')).toEqual(['sym-2']);
    expect(params.getAll('affinity_symbol_exclude_ids')).toEqual(['sym-2']);
    expect(params.get('affinity_symbol_match')).toBe('all');
    expect(params.getAll('devotion_symbol_ids')).toEqual(['sym-3']);
    expect(params.getAll('devotion_symbol_exclude_ids')).toEqual(['sym-3']);
    expect(params.get('devotion_symbol_match')).toBe('any');
    expect(params.getAll('other_symbol_ids')).toEqual(['sym-4']);
    expect(params.getAll('other_symbol_exclude_ids')).toEqual(['sym-4']);
    expect(params.get('other_symbol_match')).toBe('any');
    expect(params.getAll('symbol_ids')).toEqual([]);
    expect(params.getAll('type_ids')).toEqual(['type-1']);
    expect(params.getAll('type_exclude_ids')).toEqual(['type-2']);
    expect(params.get('type_match')).toBe('any');
    expect(params.get('mana_cost_min')).toBe('2');
    expect(params.get('mana_cost_max')).toBe('7');
    expect(params.getAll('keyword_keys')).toEqual([]);
    expect(payload).toMatchObject({
      lifecycle_status: 'deprecated',
      keyword_ids: ['kw-1'],
      keyword_match: 'all',
      tag_ids: ['tag-1'],
      tag_match: 'all',
      mana_family_keys: ['arcane'],
      mana_family_exclude_keys: ['arcane'],
      affinity_symbol_ids: ['sym-2'],
      affinity_symbol_exclude_ids: ['sym-2'],
      devotion_symbol_ids: ['sym-3'],
      devotion_symbol_exclude_ids: ['sym-3'],
      other_symbol_ids: ['sym-4'],
      other_symbol_exclude_ids: ['sym-4'],
      type_ids: ['type-1'],
      type_exclude_ids: ['type-2'],
      mana_cost_min: '2',
      mana_cost_max: '7',
    });
  });
});
