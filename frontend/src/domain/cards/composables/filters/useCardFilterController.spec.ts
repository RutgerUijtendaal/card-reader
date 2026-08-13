import { describe, expect, test } from 'vitest';
import { useCardFilterController } from '@/domain/cards/composables/filters/useCardFilterController';

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
    state.onUpdateSelectedTypeIds(['type-1']);
    state.onUpdateExcludedTypeIds(['type-2']);
    state.onUpdateTypeMatch('all');
    state.onUpdateCardPool('evil');
    state.onUpdateSelectedCardRoles(['boss']);
    state.onUpdateExcludedCardRoles([]);
    state.onUpdateCardRoleMatch('all');
    state.onUpdateSelectedCardFactions(['order']);
    state.onUpdateExcludedCardFactions(['blood']);
    state.onUpdateCardFactionMatch('all');

    state.resetManaGroup();
    state.resetKeywordGroup();
    state.resetTypeGroup();
    state.resetCardRoleGroup();

    expect(controller.selectionState.value.cardPool).toBe('evil');
    expect(controller.selectionState.value.cardRoleIds).toEqual([]);
    expect(controller.selectionState.value.cardRoleExcludeIds).toEqual(['hero']);
    expect(controller.selectionState.value.cardRoleMatch).toBe('any');
    expect(controller.selectionState.value.cardFactionIds).toEqual(['order']);
    expect(controller.selectionState.value.cardFactionExcludeIds).toEqual(['blood']);
    expect(controller.selectionState.value.cardFactionMatch).toBe('all');

    state.resetCardFactionGroup();

    expect(controller.selectionState.value.manaTypeSymbolIds).toEqual([]);
    expect(controller.selectionState.value.manaTypeSymbolExcludeIds).toEqual([]);
    expect(controller.selectionState.value.manaSymbolMatch).toBe('any');
    expect(controller.selectionState.value.manaCostMin).toBe('');
    expect(controller.selectionState.value.manaCostMax).toBe('');
    expect(controller.selectionState.value.keywordIds).toEqual([]);
    expect(controller.selectionState.value.keywordMatch).toBe('any');
    expect(controller.selectionState.value.typeIds).toEqual([]);
    expect(controller.selectionState.value.typeExcludeIds).toEqual([]);
    expect(controller.selectionState.value.typeMatch).toBe('any');
    expect(controller.selectionState.value.cardPool).toBe('evil');
    expect(controller.selectionState.value.cardRoleExcludeIds).toEqual(['hero']);
    expect(controller.selectionState.value.cardFactionIds).toEqual([]);
    expect(controller.selectionState.value.cardFactionExcludeIds).toEqual([]);
    expect(controller.selectionState.value.cardFactionMatch).toBe('any');
  });
});
