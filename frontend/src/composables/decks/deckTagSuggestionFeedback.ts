import type { DeckTagSuggestionResult } from '@/modules/decks/types';

export const getDeckTagSuggestionFeedback = (
  results: DeckTagSuggestionResult[] | undefined,
): string | null => {
  const rejected = (results ?? []).filter((result) => result.status === 'rejected');
  if (rejected.length === 0) {
    return null;
  }
  if (rejected.length === 1) {
    return rejected[0].message ?? 'That deck tag suggestion was previously declined.';
  }
  return `${rejected.length} deck tag suggestions were previously declined. Try more specific labels.`;
};
