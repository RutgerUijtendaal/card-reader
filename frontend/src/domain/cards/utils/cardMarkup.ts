import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';
import type { SymbolFilterOption } from '@/domain/cards/types';

const cardReferencePattern = /^\[\[card:([^|\]\\\s]+)\|((?:\\.|[^\]\\])+)\]\]/;
const symbolReferencePattern = /^\[\[symbol:([a-z0-9-]+)\]\]/;
const escapedCardCharacterPattern = /\\([\\|\]])/g;

export type CardMarkupTrigger = {
  start: number;
  end: number;
  kind: 'all' | 'card' | 'symbol';
  query: string;
};

type CardReferenceMeta = { kind: 'card'; id: string; label: string };
type SymbolReferenceMeta = { kind: 'symbol'; key: string };
type ReferenceMeta = CardReferenceMeta | SymbolReferenceMeta;
type MarkupToken = {
  type: string;
  content: string;
  meta: unknown;
  children: MarkupToken[] | null;
};

export const buildCardReference = (cardId: string, displayLabel: string): string => {
  const escapedLabel = displayLabel
    .replace(/\\/g, '\\\\')
    .replace(/\|/g, '\\|')
    .replace(/\]/g, '\\]');
  return `[[card:${cardId}|${escapedLabel}]]`;
};

export const buildSymbolReference = (key: string): string =>
  `[[symbol:${key.trim().toLowerCase()}]]`;

export const findCardMarkupTrigger = (value: string, caret: number): CardMarkupTrigger | null => {
  const beforeCaret = value.slice(0, caret);
  const start = beforeCaret.lastIndexOf('[[');
  const closeAfterCaret = start >= 0 ? value.indexOf(']]', Math.max(caret, start + 2)) : -1;
  const nextOpenAfterCaret = start >= 0 ? value.indexOf('[[', Math.max(caret, start + 2)) : -1;
  const completedAfterCaret =
    closeAfterCaret >= 0 && (nextOpenAfterCaret < 0 || closeAfterCaret < nextOpenAfterCaret);
  if (
    start < 0 ||
    beforeCaret.slice(start).includes(']]') ||
    completedAfterCaret ||
    isEscapedAt(value, start) ||
    isInsideCode(value, start)
  ) {
    return null;
  }
  const fragment = beforeCaret.slice(start + 2);
  if (fragment.startsWith('card:')) {
    return { start, end: caret, kind: 'card', query: fragment.slice(5) };
  }
  if (fragment.startsWith('symbol:')) {
    return { start, end: caret, kind: 'symbol', query: fragment.slice(7) };
  }
  if (fragment.includes(':')) {
    return null;
  }
  return { start, end: caret, kind: 'all', query: fragment };
};

export const renderCardMarkupHtml = (
  markup: string,
  symbols: readonly SymbolFilterOption[] = [],
): string => {
  const symbolByKey = new Map(symbols.map((symbol) => [symbol.key, symbol]));
  const markdown = createMarkupParser(symbolByKey);
  markdown.disable('image');
  markdown.validateLink = (url) => /^(?:https?:|mailto:|\/|#)/i.test(url);
  const defaultLinkOpen = markdown.renderer.rules.link_open;
  markdown.renderer.rules.link_open = (tokens, index, options, environment, renderer) => {
    const token = tokens[index];
    const href = String(token?.attrGet('href') ?? '');
    if (/^https?:/i.test(href)) {
      token?.attrSet('target', '_blank');
      token?.attrSet('rel', 'noopener noreferrer');
    }
    return defaultLinkOpen
      ? defaultLinkOpen(tokens, index, options, environment, renderer)
      : renderer.renderToken(tokens, index, options);
  };
  return DOMPurify.sanitize(markdown.render(markup), {
    ALLOWED_TAGS: [
      'a',
      'blockquote',
      'br',
      'code',
      'em',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'li',
      'ol',
      'p',
      'pre',
      'strong',
      'ul',
      'span',
    ],
    ALLOWED_ATTR: ['class', 'data-card-reference-id', 'href', 'rel', 'target'],
  });
};

export const extractSymbolReferenceKeys = (markup: string): string[] => {
  const tokens = createMarkupParser(new Map()).parse(markup, {});
  const keys: string[] = [];
  visitTokens(tokens, (token) => {
    const meta = token.meta as ReferenceMeta | null;
    if (token.type === 'symbol_reference' && meta?.kind === 'symbol') keys.push(meta.key);
  });
  return keys;
};

const isInsideCode = (value: string, position: number): boolean => {
  const marker = unusedMarker(value, 'CARDREADERCARETPOSITION');
  const markedValue = `${value.slice(0, position)}${marker}${value.slice(position)}`;
  const markdown = new MarkdownIt('commonmark', { html: false });
  let inside = false;
  visitTokens(markdown.parse(markedValue, {}), (token) => {
    if (['code_inline', 'code_block', 'fence'].includes(token.type) && token.content.includes(marker)) {
      inside = true;
    }
  });
  return inside;
};

const createMarkupParser = (
  symbolByKey: ReadonlyMap<string, SymbolFilterOption>,
): InstanceType<typeof MarkdownIt> => {
  const markdown = new MarkdownIt('commonmark', {
    html: false,
    breaks: true,
    linkify: false,
    typographer: false,
  });
  markdown.inline.ruler.before('text', 'card_reader_reference', (state, silent) => {
    const remaining = state.src.slice(state.pos);
    const cardMatch = remaining.match(cardReferencePattern);
    const symbolMatch = remaining.match(symbolReferencePattern);
    const match = cardMatch ?? symbolMatch;
    if (!match) return false;
    if (!silent) {
      if (cardMatch) {
        const token = state.push('card_reference', '', 0);
        token.meta = {
          kind: 'card',
          id: cardMatch[1] ?? '',
          label: (cardMatch[2] ?? '').replace(escapedCardCharacterPattern, '$1'),
        } satisfies CardReferenceMeta;
      } else {
        const token = state.push('symbol_reference', '', 0);
        token.meta = { kind: 'symbol', key: symbolMatch?.[1] ?? '' } satisfies SymbolReferenceMeta;
      }
    }
    state.pos += match[0].length;
    return true;
  });
  markdown.renderer.rules.card_reference = (tokens, index) => {
    const meta = tokens[index]?.meta as ReferenceMeta | null;
    if (meta?.kind !== 'card') return '';
    return `<a class="card-markup-reference" data-card-reference-id="${escapeHtml(meta.id)}" href="/cards/${encodeURIComponent(meta.id)}">${escapeHtml(meta.label)}</a>`;
  };
  markdown.renderer.rules.symbol_reference = (tokens, index) => {
    const meta = tokens[index]?.meta as ReferenceMeta | null;
    if (meta?.kind !== 'symbol') return '';
    const symbol = symbolByKey.get(meta.key);
    return `<span class="card-markup-symbol" title="${escapeHtml(symbol?.label ?? meta.key)}">${escapeHtml(symbol?.text_token || meta.key)}</span>`;
  };
  return markdown;
};

const visitTokens = (
  tokens: readonly MarkupToken[],
  visitor: (token: MarkupToken) => void,
): void => {
  for (const token of tokens) {
    visitor(token);
    if (token.children) visitTokens(token.children, visitor);
  }
};

const isEscapedAt = (value: string, position: number): boolean => {
  let backslashes = 0;
  for (let index = position - 1; index >= 0 && value[index] === '\\'; index -= 1) backslashes += 1;
  return backslashes % 2 === 1;
};

const unusedMarker = (value: string, base: string): string => {
  let marker = base;
  while (value.includes(marker)) marker += 'X';
  return marker;
};

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
