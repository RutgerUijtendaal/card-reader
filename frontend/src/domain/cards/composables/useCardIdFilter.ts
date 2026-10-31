import { computed, type Ref } from 'vue';

/** Keep collection queries stable until the enabled filter's membership changes. */
export const useCardIdFilter = (
  cardIds: Readonly<Ref<string[]>>,
  enabled: Readonly<Ref<boolean>>,
  emptySentinel: string,
) => {
  const empty: string[] = [];
  const emptySelection = [emptySentinel];
  let previousSignature = '';
  let previousIds = empty;

  return computed(() => {
    if (!enabled.value) {
      previousSignature = '';
      previousIds = empty;
      return empty;
    }
    if (cardIds.value.length === 0) {
      previousSignature = emptySentinel;
      previousIds = emptySelection;
      return emptySelection;
    }
    const ids = [...new Set(cardIds.value)].sort((left, right) => left.localeCompare(right));
    const signature = ids.join('\u0000');
    if (signature === previousSignature) return previousIds;
    previousSignature = signature;
    previousIds = ids;
    return ids;
  });
};
