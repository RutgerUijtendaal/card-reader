import { describe, expect, it } from 'vitest';
import {
  buildCreatePayload,
  CATALOG_KIND_GROUPS,
  createEmptyCatalogEntry,
  isKnownCatalogKind,
  isSuggestedCatalogKind,
  kindLabel,
  normalizeCatalogResponse,
} from './catalogAdmin';

describe('catalogAdminUtils', () => {
  it('groups card catalog and deck tag kinds separately', () => {
    expect(CATALOG_KIND_GROUPS).toEqual([
      {
        label: 'Card catalog',
        kinds: ['keywords', 'tags', 'symbols', 'types', 'suggested-tags', 'suggested-types'],
      },
      { label: 'Deck tags', kinds: ['deck-roles', 'deck-types', 'suggested-deck-types'] },
    ]);
    expect(isKnownCatalogKind('tags')).toBe(true);
    expect(isKnownCatalogKind('deck-roles')).toBe(true);
    expect(isSuggestedCatalogKind('suggested-types')).toBe(true);
    expect(isSuggestedCatalogKind('suggested-deck-types')).toBe(true);
    expect(kindLabel('suggested-tags')).toBe('Suggested tags');
    expect(kindLabel('suggested-types')).toBe('Suggested types');
  });

  it('builds deck tag catalog payloads without card identifiers', () => {
    const entry = createEmptyCatalogEntry();
    entry.label = 'Damage';
    entry.key = 'damage';
    entry.identifiers_text = 'ignored';

    expect(buildCreatePayload('deck-roles', entry)).toEqual({
      kind: 'role',
      label: 'Damage',
      key: 'damage',
    });
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
