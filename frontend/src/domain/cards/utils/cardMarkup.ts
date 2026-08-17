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
  if (start < 0 || beforeCaret.slice(start).includes(']]') || isInsideCode(value, start)) {
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
  const { markup: protectedMarkup, references } = protectReferences(markup, symbolByKey);
  const markdown = new MarkdownIt({
    html: false,
    breaks: true,
    linkify: false,
    typographer: false,
  });
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
  let html = markdown.render(protectedMarkup);
  for (const [placeholder, rendered] of references) {
    html = html.replaceAll(placeholder, rendered);
  }
  return DOMPurify.sanitize(html, {
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

const protectReferences = (
  markup: string,
  symbolByKey: ReadonlyMap<string, SymbolFilterOption>,
): { markup: string; references: Map<string, string> } => {
  const output: string[] = [];
  const references = new Map<string, string>();
  let position = 0;
  let fenceMarker: '`' | '~' | null = null;
  let inlineTicks = 0;
  let atLineStart = true;
  while (position < markup.length) {
    const remaining = markup.slice(position);
    if (atLineStart && inlineTicks === 0) {
      const fence = remaining.match(/^ {0,3}(`{3,}|~{3,})/);
      if (fence?.[1]) {
        const marker = fence[1][0] as '`' | '~';
        fenceMarker = fenceMarker === null ? marker : marker === fenceMarker ? null : fenceMarker;
      }
    }
    if (fenceMarker === null && markup[position] === '`') {
      const ticks = remaining.match(/^`+/)?.[0] ?? '`';
      inlineTicks =
        inlineTicks === 0 ? ticks.length : ticks.length === inlineTicks ? 0 : inlineTicks;
      output.push(ticks);
      position += ticks.length;
      atLineStart = false;
      continue;
    }
    if (fenceMarker === null && inlineTicks === 0) {
      const cardMatch = remaining.match(cardReferencePattern);
      const symbolMatch = remaining.match(symbolReferencePattern);
      const match = cardMatch ?? symbolMatch;
      if (match) {
        const placeholder = `CARDREADERREFERENCETOKEN${references.size}X`;
        if (cardMatch) {
          const id = cardMatch[1] ?? '';
          const label = (cardMatch[2] ?? '').replace(escapedCardCharacterPattern, '$1');
          references.set(
            placeholder,
            `<a class="card-markup-reference" data-card-reference-id="${escapeHtml(id)}" href="/cards/${encodeURIComponent(id)}">${escapeHtml(label)}</a>`,
          );
        } else {
          const key = symbolMatch?.[1] ?? '';
          const symbol = symbolByKey.get(key);
          references.set(
            placeholder,
            `<span class="card-markup-symbol" title="${escapeHtml(symbol?.label ?? key)}">${escapeHtml(symbol?.text_token || key)}</span>`,
          );
        }
        output.push(placeholder);
        position += match[0].length;
        atLineStart = false;
        continue;
      }
    }
    const character = markup[position] ?? '';
    output.push(character);
    position += 1;
    atLineStart = character === '\n';
  }
  return { markup: output.join(''), references };
};

const isInsideCode = (value: string, position: number): boolean => {
  const before = value.slice(0, position);
  const fenceMatches = before.match(/(^|\n) {0,3}(`{3,}|~{3,})/g) ?? [];
  if (fenceMatches.length % 2 === 1) return true;
  const line = before.slice(before.lastIndexOf('\n') + 1);
  return (line.match(/`+/g)?.length ?? 0) % 2 === 1;
};

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
