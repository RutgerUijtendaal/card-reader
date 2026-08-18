import { describe, expect, it } from 'vitest';
import {
  buildCardReference,
  findCardMarkupTrigger,
  renderCardMarkupHtml,
} from '@/domain/cards/utils/cardMarkup';

describe('card markup', () => {
  it('renders Markdown and sanitized card references', () => {
    const source = `## Plan\n\nPlay **${buildCardReference('card-1', 'Hero | One]')}**.`;

    const html = renderCardMarkupHtml(source);

    expect(html).toContain('<h2>Plan</h2>');
    expect(html).toContain('data-card-reference-id="card-1"');
    expect(html).toContain('Hero | One]');
  });

  it('avoids collisions with authored placeholder-like text', () => {
    const html = renderCardMarkupHtml(
      'CARDREADERREFERENCETOKEN0X [[card:card-1|Hero]]',
    );

    expect(html).toContain('CARDREADERREFERENCETOKEN0X');
    expect(html.match(/data-card-reference-id/g)).toHaveLength(1);
  });

  it('keeps references in inline and fenced code literal', () => {
    const html = renderCardMarkupHtml(
      '`[[card:card-1|Hero]]`\n\n```\n[[card:card-2|Villain]]\n```',
    );

    expect(html).not.toContain('data-card-reference-id');
    expect(html).toContain('[[card:card-1|Hero]]');
    expect(html).toContain('[[card:card-2|Villain]]');
  });

  it('keeps references in indented code blocks literal', () => {
    const html = renderCardMarkupHtml('    [[card:card-1|Indented]]\n\t[[symbol:fire]]');

    expect(html).not.toContain('data-card-reference-id');
    expect(html).toContain('[[card:card-1|Indented]]');
    expect(html).toContain('[[symbol:fire]]');
  });

  it('resumes resolving references after a closing fence', () => {
    const html = renderCardMarkupHtml(
      '```\n[[card:card-1|Inside]]\n```\n\n[[card:card-2|Outside]]',
    );

    expect(html).toContain('[[card:card-1|Inside]]');
    expect(html).not.toContain('data-card-reference-id="card-1"');
    expect(html).toContain('data-card-reference-id="card-2"');
  });

  it('requires a sufficiently long, otherwise empty closing fence', () => {
    const html = renderCardMarkupHtml(
      '````\n[[card:card-1|Inside one]]\n```\n[[card:card-2|Inside two]]\n```` not closed\n[[card:card-3|Inside three]]\n````\n\n[[card:card-4|Outside]]',
    );

    expect(html).not.toContain('data-card-reference-id="card-1"');
    expect(html).not.toContain('data-card-reference-id="card-2"');
    expect(html).not.toContain('data-card-reference-id="card-3"');
    expect(html).toContain('data-card-reference-id="card-4"');
  });

  it('disables raw HTML, images, and unsafe URL protocols', () => {
    const html = renderCardMarkupHtml(
      '<script>alert(1)</script> ![alt](https://example.com/a.png) [bad](javascript:alert(1))',
    );

    expect(html).not.toContain('<script');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('href="javascript:');
  });

  it('adds safe external-link attributes', () => {
    const html = renderCardMarkupHtml('[site](https://example.com)');

    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
  });

  it('renders card references as plain labels inside Markdown links', () => {
    const html = renderCardMarkupHtml(
      '[see [[card:card-1|Card One]]](https://example.com)',
    );

    expect(html).toContain('<a href="https://example.com"');
    expect(html).toContain('see Card One</a>');
    expect(html).not.toContain('data-card-reference-id');
  });

  it('uses CommonMark without default-preset extensions', () => {
    expect(renderCardMarkupHtml('~~literal~~')).toContain('~~literal~~');
  });

  it('finds unified and narrowed autocomplete triggers outside code', () => {
    expect(findCardMarkupTrigger('Use [[dra', 9)).toMatchObject({ kind: 'all', query: 'dra' });
    expect(findCardMarkupTrigger('Use [[card:hero', 15)).toMatchObject({
      kind: 'card',
      query: 'hero',
    });
    expect(findCardMarkupTrigger('`[[card:hero`', 13)).toBeNull();
    expect(findCardMarkupTrigger('`[[card:hero', 13)).toMatchObject({
      kind: 'card',
      query: 'hero',
    });
  });

  it('ignores autocomplete inside completed references and indented code', () => {
    const completed = '[[card:old|Old]]';

    expect(findCardMarkupTrigger(completed, completed.indexOf('old') + 2)).toBeNull();
    expect(findCardMarkupTrigger('    [[card:hero', 15)).toBeNull();
  });

  it('scopes completion detection to the active trigger', () => {
    const value = '[[new before [[card:id|Existing]]';

    expect(findCardMarkupTrigger(value, '[[new'.length)).toMatchObject({
      kind: 'all',
      query: 'new',
    });
  });

  it('resolves references after unmatched backticks', () => {
    const html = renderCardMarkupHtml('`note [[card:card-1|Hero]]');

    expect(html).toContain('data-card-reference-id="card-1"');
  });

  it('does not match inline-code delimiters across CommonMark blocks', () => {
    const source = '`note\n\n[[card:card-1|Hero]]`';
    const activeTrigger = '`note\n\n[[card:hero`';
    const html = renderCardMarkupHtml(source);

    expect(html).toContain('data-card-reference-id="card-1"');
    expect(findCardMarkupTrigger(activeTrigger, activeTrigger.length - 1)).toMatchObject({
      kind: 'card',
      query: 'hero',
    });
  });

  it('keeps escaped references literal and suppresses their autocomplete', () => {
    const source = '\\[[card:card-1|Hero]] \\[[symbol:fire]]';
    const html = renderCardMarkupHtml(source);

    expect(html).not.toContain('data-card-reference-id');
    expect(html).toContain('[[card:card-1|Hero]]');
    expect(html).toContain('[[symbol:fire]]');
    expect(findCardMarkupTrigger('\\[[card:hero', 13)).toBeNull();
  });
});
