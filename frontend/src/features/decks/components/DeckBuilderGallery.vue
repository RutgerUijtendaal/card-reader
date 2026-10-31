<template>
  <CardBuilderGallery
    :gallery="controller.gallery"
    :loading="loading"
    :hover-mode="controller.filters.hoverMode.value"
    :selection-mode="controller.deck.isHeroStep.value"
    :is-selected="card => card.result_type === 'card' && controller.deck.isHeroStep.value && controller.deck.form.hero_card_id === card.id"
    :action-label="card => card.result_type === 'card' ? controller.deck.galleryActionLabel(card) : 'Card unavailable'"
    :action-disabled="card => card.result_type !== 'card' || controller.deck.galleryActionDisabled(card)"
    :remove-disabled="controller.deck.galleryRemoveActionDisabled"
    :quantity="controller.deck.getEntryQuantity"
    :activate="card => { if (card.result_type === 'card') controller.deck.handleGalleryAction(card); }"
    :remove="controller.deck.handleGalleryRemoveAction"
    :empty-message="controller.deck.isHeroStep.value ? 'No hero cards found for the current search.' : 'No cards found for the current filters.'"
  />
</template>
<script setup lang="ts">
import CardBuilderGallery from '@/domain/cards/components/CardBuilderGallery.vue';
import type { DeckEditorController } from '../composables/useDeckEditor';
withDefaults(defineProps<{ controller: DeckEditorController; loading?: boolean }>(), { loading: false });
</script>
