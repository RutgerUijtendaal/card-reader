<template>
  <CardBuilderFilterBar
    :filters="controller.filters"
    :total-count="controller.gallery.totalCount.value"
    :search-placeholder="controller.deck.isHeroStep.value ? 'Search heroes...' : 'Search cards...'"
    :result-noun="controller.deck.isHeroStep.value ? ['hero', 'heroes'] : ['card', 'cards']"
    :show-current-only="controller.deck.isCardsStep.value"
    current-only-label="In deck"
    :visible-sections="controller.deck.isHeroStep.value ? ['mana', 'affinity'] : DECK_BUILDER_VISIBLE_FILTER_SECTIONS"
  />
</template>
<script setup lang="ts">
import CardBuilderFilterBar from '@/domain/cards/components/CardBuilderFilterBar.vue';
import type { DeckEditorController } from '../composables/useDeckEditor';
import { DECK_BUILDER_VISIBLE_FILTER_SECTIONS } from '../utils/deckBuilderFilterPolicy';

defineProps<{ controller: DeckEditorController }>();
</script>
