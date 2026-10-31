<template>
  <CardBuilderFiltersPanel
    :filters="controller.filters"
    :total-count="controller.gallery.totalCount.value"
    :title="controller.deck.isHeroStep.value ? 'Hero Gallery' : 'Card Gallery'"
    :description="controller.deck.isHeroStep.value ? 'Browse hero cards.' : 'Search and filter cards.'"
    :search-placeholder="controller.deck.isHeroStep.value ? 'Search heroes...' : 'Search cards...'"
    :show-current-only="controller.deck.isCardsStep.value"
    current-only-label="Current Deck Only"
    :visible-sections="controller.deck.isHeroStep.value ? ['mana', 'affinity'] : DECK_BUILDER_VISIBLE_FILTER_SECTIONS"
    :default-open-sections="controller.deck.isHeroStep.value ? ['mana', 'affinity'] : undefined"
  >
    <div
      v-if="controller.deck.isHeroStep.value"
      class="theme-muted-panel space-y-3 p-3"
    >
      <p class="theme-section-title text-sm font-semibold">
        Setup
      </p>
      <p class="theme-section-muted text-sm">
        Choose a hero for this deck. Use mana type or unmatched affinity to narrow the hero pool.
      </p>
    </div>
  </CardBuilderFiltersPanel>
</template>
<script setup lang="ts">
import CardBuilderFiltersPanel from '@/domain/cards/components/CardBuilderFiltersPanel.vue';
import type { DeckEditorController } from '../composables/useDeckEditor';
import { DECK_BUILDER_VISIBLE_FILTER_SECTIONS } from '../utils/deckBuilderFilterPolicy';
defineProps<{ controller: DeckEditorController }>();
</script>
