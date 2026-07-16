import { describe, expect, test } from 'vitest';
import {
  getTriStateSelection,
  getTriStateSelectionClass,
  getTriStateSelectionLabel,
  setAllTriStateSelections,
  toggleTriStateSelection,
} from '@/composables/card-filters/triStateSelection';

describe('tri-state selection', () => {
  test('resolves selection state, presentation, and accessible labels', () => {
    expect(getTriStateSelection('spell', ['spell'], [])).toBe('include');
    expect(getTriStateSelection('spell', [], ['spell'])).toBe('exclude');
    expect(getTriStateSelection('spell', [], [])).toBe('off');
    expect(getTriStateSelectionClass('include')).toBe('theme-choice-chip-include');
    expect(getTriStateSelectionClass('exclude')).toBe('theme-choice-chip-exclude');
    expect(getTriStateSelectionClass('off')).toBe('');
    expect(getTriStateSelectionLabel('Spell', 'include')).toBe('Spell included. Click to exclude.');
    expect(getTriStateSelectionLabel('Spell', 'exclude')).toBe('Spell excluded. Click to clear.');
    expect(getTriStateSelectionLabel('Spell', 'off')).toBe('Spell not filtered. Click to include.');
  });

  test('cycles off through include and exclude without overlapping lists', () => {
    const included = toggleTriStateSelection('spell', [], []);
    expect(included).toEqual({ included: ['spell'], excluded: [] });

    const excluded = toggleTriStateSelection('spell', included.included, included.excluded);
    expect(excluded).toEqual({ included: [], excluded: ['spell'] });

    const cleared = toggleTriStateSelection('spell', excluded.included, excluded.excluded);
    expect(cleared).toEqual({ included: [], excluded: [] });
  });

  test('sets every available key to one state', () => {
    expect(setAllTriStateSelections(['spell', 'follower'], 'include')).toEqual({
      included: ['spell', 'follower'],
      excluded: [],
    });
    expect(setAllTriStateSelections(['spell', 'follower'], 'exclude')).toEqual({
      included: [],
      excluded: ['spell', 'follower'],
    });
    expect(setAllTriStateSelections(['spell', 'follower'], 'off')).toEqual({
      included: [],
      excluded: [],
    });
  });
});
