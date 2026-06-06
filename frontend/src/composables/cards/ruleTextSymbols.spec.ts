import { describe, expect, it } from 'vitest';

import {
  applySymbolAutocomplete,
  buildEffectiveSymbolIds,
  buildSymbolPlaceholder,
  findActiveSymbolTrigger,
  getRuleTextSymbolState,
} from './ruleTextSymbols';

const symbols = [
  { id: 'sym-1', key: 'exhaust', label: 'Exhaust', symbol_type: 'other', text_token: '{EXHAUST}', asset_url: null },
  { id: 'sym-2', key: 'fire-mana', label: 'Fire Mana', symbol_type: 'mana', text_token: '{FM}', asset_url: null },
];

describe('ruleTextSymbols', () => {
  it('parses referenced and unknown symbol keys from enriched text', () => {
    expect(
      getRuleTextSymbolState(
        '[[symbol:exhaust]]: Gain [[symbol:fire-mana]] and [[symbol:missing]].',
        symbols,
      ),
    ).toEqual({
      referencedKeys: ['exhaust', 'fire-mana', 'missing'],
      referencedSymbolIds: ['sym-1', 'sym-2'],
      unknownKeys: ['missing'],
    });
  });

  it('deduplicates merged effective symbol ids', () => {
    expect(buildEffectiveSymbolIds(['sym-1'], ['sym-2', 'sym-1'])).toEqual(['sym-1', 'sym-2']);
  });

  it('normalizes inserted symbol placeholders', () => {
    expect(buildSymbolPlaceholder(' Exhaust ')).toBe('[[symbol:exhaust]]');
  });

  it('finds an active trigger for inline autocomplete', () => {
    expect(findActiveSymbolTrigger('Deal 2 [[symbol:exh', 20)).toEqual({
      start: 7,
      end: 19,
      query: 'exh',
    });
  });

  it('replaces the active trigger with a full placeholder', () => {
    const trigger = findActiveSymbolTrigger('Deal 2 [[exh', 12);
    expect(trigger).not.toBeNull();
    expect(
      applySymbolAutocomplete('Deal 2 [[exh', trigger!, 'exhaust'),
    ).toEqual({
      nextText: 'Deal 2 [[symbol:exhaust]]',
      nextCaretIndex: 25,
    });
  });
});
