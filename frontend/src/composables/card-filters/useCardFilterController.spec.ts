import { describe, expect, test } from 'vitest';
import { useCardFilterController } from '@/composables/card-filters/useCardFilterController';

describe('useCardFilterController', () => {
  test('resets grouped filter values through the shared sections adapter', () => {
    const controller = useCardFilterController();
    const state = controller.filterSectionsState.value;

    state.onUpdateSelectedManaTypeSymbolIds(['mana-1']);
    state.onUpdateExcludedManaTypeSymbolIds(['mana-2']);
    state.onUpdateManaSymbolMatch('all');
    state.onUpdateManaCostMin('1');
    state.onUpdateManaCostMax('4');
    state.onUpdateSelectedKeywordIds(['keyword-1']);
    state.onUpdateKeywordMatch('all');

    state.resetManaGroup();
    state.resetKeywordGroup();

    expect(controller.selectionState.value.manaTypeSymbolIds).toEqual([]);
    expect(controller.selectionState.value.manaTypeSymbolExcludeIds).toEqual([]);
    expect(controller.selectionState.value.manaSymbolMatch).toBe('any');
    expect(controller.selectionState.value.manaCostMin).toBe('');
    expect(controller.selectionState.value.manaCostMax).toBe('');
    expect(controller.selectionState.value.keywordIds).toEqual([]);
    expect(controller.selectionState.value.keywordMatch).toBe('any');
  });
});
