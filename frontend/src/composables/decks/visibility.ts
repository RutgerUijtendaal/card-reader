import type { DeckVisibility } from '@/modules/decks/types';

export const deckVisibilityOptions: Array<{ value: DeckVisibility; label: string; description: string }> = [
  { value: 'private', label: 'Private', description: 'Only you can view this deck.' },
  { value: 'unlisted', label: 'Unlisted', description: 'Anyone with the link can view this deck.' },
  { value: 'public', label: 'Public', description: 'Listed for everyone to discover.' },
];

export const deckVisibilityLabels: Record<DeckVisibility, string> = {
  private: 'Private',
  unlisted: 'Unlisted',
  public: 'Public',
};

export const deckVisibilityDescriptions: Record<DeckVisibility, string> = {
  private: 'Only you can view this deck.',
  unlisted: 'Anyone with the link can view this deck.',
  public: 'Listed for everyone to discover.',
};

export const deckVisibilityBadgeClasses: Record<DeckVisibility, string> = {
  private: 'theme-pill-neutral',
  unlisted: 'theme-pill-keyword',
  public: 'theme-pill-accent',
};
