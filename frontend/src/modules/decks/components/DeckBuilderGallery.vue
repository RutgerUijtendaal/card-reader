<template>
  <div class="app-scrollbar min-h-0 overflow-y-auto pr-1">
    <div class="space-y-6">
      <div
        class="grid gap-6"
        :style="controller.gallery.galleryGridStyle.value"
      >
        <article
          v-for="card in controller.gallery.galleryCards.value"
          :key="card.id"
          class="theme-card-frame justify-self-center space-y-3 rounded-3xl p-3"
          :style="{
            width: `${controller.gallery.galleryTileWidthRem.value}rem`,
            maxWidth: '100%',
          }"
        >
          <CardGalleryItem
            :card="card"
            :tooltip-enabled="controller.filters.tooltipEnabled.value"
            :card-height-rem="controller.gallery.cardHeightRem.value"
            activation-mode="emit"
            activation-label="Add card to deck"
            :activation-disabled="controller.deck.galleryActionDisabled(card)"
            @activate="handleActivate"
          />

          <button
            class="btn-secondary w-full justify-center"
            type="button"
            :disabled="controller.deck.galleryActionDisabled(card)"
            @click="controller.deck.handleGalleryAction(card)"
          >
            {{ controller.deck.galleryActionLabel(card) }}
          </button>
        </article>
      </div>

      <div
        v-if="controller.gallery.galleryCards.value.length > 0"
        ref="sentinelRef"
        class="theme-section-muted flex justify-center py-4 text-sm"
      >
        <span v-if="controller.gallery.isLoadingPage.value">Loading more cards...</span>
        <span v-else-if="controller.gallery.nextPage.value === null">All cards loaded.</span>
        <span v-else>Scroll to load more.</span>
      </div>

      <div
        v-if="!controller.gallery.isLoadingInitial.value && controller.gallery.galleryCards.value.length === 0"
        class="page-card theme-section-muted text-sm"
      >
        {{ controller.deck.isSetupStep.value ? 'No hero cards found for the current search.' : 'No cards found for the current filters.' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watchEffect, ref } from 'vue';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import type { GalleryItem } from '@/modules/card-detail/types';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const sentinelRef = ref<HTMLElement | null>(null);

const handleActivate = (card: GalleryItem): void => {
  if (card.result_type !== 'card') {
    return;
  }
  props.controller.deck.handleGalleryAction(card);
};

watchEffect(() => {
  props.controller.gallery.setLoadMoreSentinel(sentinelRef.value);
});
</script>
