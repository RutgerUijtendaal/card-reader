import { describe, expect, it } from 'vitest';
import {
  CATALOG_KIND_GROUPS,
  isKnownCatalogKind,
  isSuggestedCatalogKind,
  normalizeCatalogResponse,
} from './catalogAdminUtils';

describe('catalogAdminUtils', () => {
  it('groups known and suggested catalog kinds separately', () => {
    expect(CATALOG_KIND_GROUPS).toEqual([
      { label: 'Known', kinds: ['keywords', 'tags', 'symbols', 'types'] },
      { label: 'Suggested', kinds: ['suggested-tags', 'suggested-types'] },
    ]);
    expect(isKnownCatalogKind('tags')).toBe(true);
    expect(isSuggestedCatalogKind('suggested-types')).toBe(true);
  });

  it('normalizes grouped catalog responses including suggestions', () => {
    const normalized = normalizeCatalogResponse({
      known: {
        keywords: [{ id: 'k1', key: 'turn-start', label: 'Turn Start', identifiers: ['turn start'], identifiers_text: '' }],
        tags: [{ id: 't1', key: 'weapon', label: 'Weapon', identifiers: ['weapon'], identifiers_text: '' }],
        symbols: [],
        types: [{ id: 'ty1', key: 'persistent', label: 'Persistent', identifiers: ['persistent'], identifiers_text: '' }],
      },
      suggested: {
        tags: [
          {
            id: 's1',
            kind: 'tag',
            display_value: 'Mystic Relic',
            normalized_value: 'mystic relic',
            status: 'pending',
            occurrence_count: 2,
            accepted_target: null,
            occurrences: [],
          },
        ],
        types: [],
      },
    });

    expect(normalized.known.tags[0].identifiers_text).toBe('weapon');
    expect(normalized.suggested.tags[0].label).toBe('Mystic Relic');
    expect(normalized.suggested.tags[0].occurrence_count).toBe(2);
  });
});
