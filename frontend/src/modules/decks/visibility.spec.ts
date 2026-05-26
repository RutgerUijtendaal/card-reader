import { describe, expect, test } from 'vitest';
import { deckVisibilityBadgeClasses, deckVisibilityDescriptions, deckVisibilityLabels, deckVisibilityOptions } from '@/modules/decks/visibility';

describe('deck visibility helpers', () => {
  test('exposes labels and descriptions for every visibility state', () => {
    expect(deckVisibilityOptions).toEqual([
      { value: 'private', label: 'Private', description: 'Only you can view this deck.' },
      { value: 'unlisted', label: 'Unlisted', description: 'Anyone with the link can view this deck.' },
      { value: 'public', label: 'Public', description: 'Listed for everyone to discover.' },
    ]);
    expect(deckVisibilityLabels.unlisted).toBe('Unlisted');
    expect(deckVisibilityDescriptions.public).toBe('Listed for everyone to discover.');
  });

  test('maps every visibility state to a badge class', () => {
    expect(deckVisibilityBadgeClasses.private).toBe('theme-pill-neutral');
    expect(deckVisibilityBadgeClasses.unlisted).toBe('theme-pill-keyword');
    expect(deckVisibilityBadgeClasses.public).toBe('theme-pill-accent');
  });
});
