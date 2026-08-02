import type { DeckDifficulty } from '@/modules/decks/types';

export const deckDifficultyOptions: Array<{ value: DeckDifficulty; label: string }> = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
];

export const deckDifficultyLabels: Record<DeckDifficulty, string> = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
};
