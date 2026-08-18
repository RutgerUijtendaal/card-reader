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
  const closeAfterCaret = start >= 0 ? value.indexOf(']]', Math.max(caret, start + 2)) : -1;
  const nextOpenAfterCaret = start >= 0 ? value.indexOf('[[', Math.max(caret, start + 2)) : -1;
  const completedAfterCaret =
    closeAfterCaret >= 0 && (nextOpenAfterCaret < 0 || closeAfterCaret < nextOpenAfterCaret);
  if (
    start < 0 ||
    beforeCaret.slice(start).includes(']]') ||
    completedAfterCaret ||
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
  const markdown = new MarkdownIt('commonmark', {
    html: false,
    breaks: true,
    linkify: false,
    typographer: false,
  });
  const { markup: protectedMarkup, references } = protectReferences(
    markup,
    symbolByKey,
    codeBlockLines(markdown, markup),
  );
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
  if (references.size > 0) {
    const placeholders = new RegExp(
      [...references.keys()].map(escapeRegExp).join('|'),
      'g',
    );
    html = html.replace(placeholders, (placeholder) => references.get(placeholder) ?? placeholder);
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
  protectedLines: ReadonlySet<number>,
): { markup: string; references: Map<string, string> } => {
  const output: string[] = [];
  const references = new Map<string, string>();
  const placeholderPrefix = unusedPlaceholderPrefix(markup);
  let position = 0;
  let lineIndex = 0;
  let inlineTicks = 0;
  let atLineStart = true;
  while (position < markup.length) {
    if (atLineStart && protectedLines.has(lineIndex)) {
      const newline = markup.indexOf('\n', position);
      const lineEnd = newline < 0 ? markup.length : newline + 1;
      output.push(markup.slice(position, lineEnd));
      position = lineEnd;
      lineIndex += 1;
      inlineTicks = 0;
      atLineStart = true;
      continue;
    }
    const remaining = markup.slice(position);
    if (markup[position] === '`') {
      const ticks = remaining.match(/^`+/)?.[0] ?? '`';
      if (
        inlineTicks === 0 &&
        hasMatchingBacktickRun(markup, position + ticks.length, ticks.length)
      ) {
        inlineTicks = ticks.length;
      } else if (ticks.length === inlineTicks) {
        inlineTicks = 0;
      }
      output.push(ticks);
      position += ticks.length;
      atLineStart = false;
      continue;
    }
    if (inlineTicks === 0) {
      const cardMatch = remaining.match(cardReferencePattern);
      const symbolMatch = remaining.match(symbolReferencePattern);
      const match = cardMatch ?? symbolMatch;
      if (match) {
        const placeholder = `${placeholderPrefix}${references.size}X`;
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
    if (atLineStart) lineIndex += 1;
  }
  return { markup: output.join(''), references };
};

const isInsideCode = (value: string, position: number): boolean => {
  const before = value.slice(0, position);
  const lineIndex = (before.match(/\n/g) ?? []).length;
  const markdown = new MarkdownIt('commonmark', { html: false });
  if (codeBlockLines(markdown, value).has(lineIndex)) return true;
  return codeSpanContainsPosition(value, position);
};

const codeSpanContainsPosition = (value: string, position: number): boolean => {
  let cursor = 0;
  while (cursor < position) {
    const opening = value.indexOf('`', cursor);
    if (opening < 0 || opening >= position) return false;
    const length = backtickRunLength(value, opening);
    const closing = matchingBacktickRun(value, opening + length, length);
    if (closing < 0) {
      cursor = opening + length;
      continue;
    }
    if (position > opening && position < closing + length) return true;
    cursor = closing + length;
  }
  return false;
};

const hasMatchingBacktickRun = (value: string, start: number, length: number): boolean =>
  matchingBacktickRun(value, start, length) >= 0;

const matchingBacktickRun = (value: string, start: number, length: number): number => {
  let cursor = start;
  while (cursor < value.length) {
    const candidate = value.indexOf('`', cursor);
    if (candidate < 0) return -1;
    const candidateLength = backtickRunLength(value, candidate);
    if (candidateLength === length) return candidate;
    cursor = candidate + candidateLength;
  }
  return -1;
};

const backtickRunLength = (value: string, start: number): number => {
  let end = start;
  while (value[end] === '`') end += 1;
  return end - start;
};

const codeBlockLines = (
  markdown: InstanceType<typeof MarkdownIt>,
  markup: string,
): Set<number> => {
  const lines = new Set<number>();
  for (const token of markdown.parse(markup, {})) {
    if (!['code_block', 'fence'].includes(token.type) || !token.map) continue;
    for (let line = token.map[0]; line < token.map[1]; line += 1) lines.add(line);
  }
  return lines;
};

const unusedPlaceholderPrefix = (markup: string): string => {
  let prefix = 'CARDREADERREFERENCETOKEN';
  while (markup.includes(prefix)) prefix += 'X';
  return prefix;
};

const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

const escapeRegExp = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
