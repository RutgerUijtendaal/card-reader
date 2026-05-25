import type { SymbolFilterOption } from '@/modules/card-detail/types';

const SYMBOL_PLACEHOLDER_PATTERN = /\[\[symbol:([a-z0-9-]+)\]\]/g;

export type RuleTextSymbolState = {
  referencedKeys: string[];
  referencedSymbolIds: string[];
  unknownKeys: string[];
};

export type ActiveSymbolTrigger = {
  start: number;
  end: number;
  query: string;
};

export const buildSymbolPlaceholder = (symbolKey: string): string =>
  `[[symbol:${symbolKey.trim().toLowerCase()}]]`;

export const getRuleTextSymbolState = (
  enrichedText: string,
  symbols: SymbolFilterOption[],
): RuleTextSymbolState => {
  const symbolsByKey = new Map(symbols.map((symbol) => [symbol.key, symbol]));
  const referencedKeys: string[] = [];
  const referencedSymbolIds: string[] = [];
  const unknownKeys: string[] = [];
  const seenKeys = new Set<string>();
  const seenIds = new Set<string>();
  const seenUnknownKeys = new Set<string>();

  for (const match of enrichedText.matchAll(SYMBOL_PLACEHOLDER_PATTERN)) {
    const symbolKey = String(match[1] ?? '').trim().toLowerCase();
    if (!symbolKey || seenKeys.has(symbolKey)) {
      continue;
    }
    seenKeys.add(symbolKey);
    referencedKeys.push(symbolKey);

    const symbol = symbolsByKey.get(symbolKey);
    if (symbol) {
      if (!seenIds.has(symbol.id)) {
        seenIds.add(symbol.id);
        referencedSymbolIds.push(symbol.id);
      }
      continue;
    }

    if (!seenUnknownKeys.has(symbolKey)) {
      seenUnknownKeys.add(symbolKey);
      unknownKeys.push(symbolKey);
    }
  }

  return {
    referencedKeys,
    referencedSymbolIds,
    unknownKeys,
  };
};

export const buildEffectiveSymbolIds = (
  referencedSymbolIds: string[],
  additionalSymbolIds: string[],
): string[] => {
  const merged = new Set<string>(referencedSymbolIds);
  for (const symbolId of additionalSymbolIds) {
    merged.add(symbolId);
  }
  return Array.from(merged);
};

export const findActiveSymbolTrigger = (
  text: string,
  caretIndex: number,
): ActiveSymbolTrigger | null => {
  const safeCaretIndex = Math.max(0, Math.min(caretIndex, text.length));
  const beforeCaret = text.slice(0, safeCaretIndex);
  const start = beforeCaret.lastIndexOf('[[');
  if (start < 0) {
    return null;
  }

  const fragment = beforeCaret.slice(start);
  if (fragment.includes(']]') || /[\r\n]/.test(fragment)) {
    return null;
  }

  const rawQuery = fragment.slice(2);
  if (/\s/.test(rawQuery)) {
    return null;
  }

  const normalizedQuery = rawQuery.toLowerCase().startsWith('symbol:')
    ? rawQuery.slice('symbol:'.length)
    : rawQuery;

  return {
    start,
    end: safeCaretIndex,
    query: normalizedQuery.trim().toLowerCase(),
  };
};

export const applySymbolAutocomplete = (
  text: string,
  trigger: ActiveSymbolTrigger,
  symbolKey: string,
): { nextText: string; nextCaretIndex: number } => {
  const placeholder = buildSymbolPlaceholder(symbolKey);
  const nextText = `${text.slice(0, trigger.start)}${placeholder}${text.slice(trigger.end)}`;
  const nextCaretIndex = trigger.start + placeholder.length;

  return {
    nextText,
    nextCaretIndex,
  };
};
