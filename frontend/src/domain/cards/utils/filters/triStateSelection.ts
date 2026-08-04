export type TriStateSelection = 'off' | 'include' | 'exclude';

export type TriStateSelectionValues = {
  included: string[];
  excluded: string[];
};

export const getTriStateSelection = (
  key: string,
  included: readonly string[],
  excluded: readonly string[],
): TriStateSelection => {
  if (included.includes(key)) {
    return 'include';
  }
  if (excluded.includes(key)) {
    return 'exclude';
  }
  return 'off';
};

export const getTriStateSelectionClass = (selection: TriStateSelection): string => {
  if (selection === 'include') {
    return 'theme-choice-chip-include';
  }
  if (selection === 'exclude') {
    return 'theme-choice-chip-exclude';
  }
  return '';
};

export const getTriStateSelectionLabel = (label: string, selection: TriStateSelection): string => {
  if (selection === 'include') {
    return `${label} included. Click to exclude.`;
  }
  if (selection === 'exclude') {
    return `${label} excluded. Click to clear.`;
  }
  return `${label} not filtered. Click to include.`;
};

export const toggleTriStateSelection = (
  key: string,
  included: readonly string[],
  excluded: readonly string[],
): TriStateSelectionValues => {
  const nextIncluded = new Set(included);
  const nextExcluded = new Set(excluded);
  const selection = getTriStateSelection(key, included, excluded);

  nextIncluded.delete(key);
  nextExcluded.delete(key);
  if (selection === 'off') {
    nextIncluded.add(key);
  } else if (selection === 'include') {
    nextExcluded.add(key);
  }

  return {
    included: Array.from(nextIncluded),
    excluded: Array.from(nextExcluded),
  };
};

export const setAllTriStateSelections = (
  keys: readonly string[],
  selection: TriStateSelection,
): TriStateSelectionValues => ({
  included: selection === 'include' ? [...keys] : [],
  excluded: selection === 'exclude' ? [...keys] : [],
});
