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

  it('keeps references in inline and fenced code literal', () => {
    const html = renderCardMarkupHtml(
      '`[[card:card-1|Hero]]`\n\n```\n[[card:card-2|Villain]]\n```',
    );

    expect(html).not.toContain('data-card-reference-id');
    expect(html).toContain('[[card:card-1|Hero]]');
    expect(html).toContain('[[card:card-2|Villain]]');
  });

  it('resumes resolving references after a closing fence', () => {
    const html = renderCardMarkupHtml(
      '```\n[[card:card-1|Inside]]\n```\n\n[[card:card-2|Outside]]',
    );

    expect(html).toContain('[[card:card-1|Inside]]');
    expect(html).not.toContain('data-card-reference-id="card-1"');
    expect(html).toContain('data-card-reference-id="card-2"');
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

  it('finds unified and narrowed autocomplete triggers outside code', () => {
    expect(findCardMarkupTrigger('Use [[dra', 9)).toMatchObject({ kind: 'all', query: 'dra' });
    expect(findCardMarkupTrigger('Use [[card:hero', 15)).toMatchObject({
      kind: 'card',
      query: 'hero',
    });
    expect(findCardMarkupTrigger('`[[card:hero', 13)).toBeNull();
  });
});
