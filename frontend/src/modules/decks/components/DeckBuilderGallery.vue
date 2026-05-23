<template>
  <div class="app-scrollbar min-h-0 overflow-y-auto pr-1">
    <div class="space-y-6">
      <div
        class="grid gap-6"
        :style="controller.galleryGridStyle.value"
      >
        <article
          v-for="card in controller.galleryCards.value"
          :key="card.id"
          class="theme-card-frame justify-self-center space-y-3 rounded-3xl p-3"
          :style="{
            width: `${controller.galleryTileWidthRem.value}rem`,
            maxWidth: '100%',
          }"
        >
          <CardGalleryItem
            :card="card"
            :tooltip-enabled="controller.tooltipEnabled.value"
            :card-height-rem="controller.cardHeightRem.value"
          />

          <button
            class="btn-secondary w-full justify-center"
            type="button"
            :disabled="controller.galleryActionDisabled(card)"
            @click="controller.handleGalleryAction(card)"
          >
            {{ controller.galleryActionLabel(card) }}
          </button>
        </article>
      </div>

      <div
        v-if="controller.galleryCards.value.length > 0"
        ref="sentinelRef"
        class="theme-section-muted flex justify-center py-4 text-sm"
      >
        <span v-if="controller.isLoadingPage.value">Loading more cards...</span>
        <span v-else-if="controller.nextPage.value === null">All cards loaded.</span>
        <span v-else>Scroll to load more.</span>
      </div>

      <div
        v-if="!controller.isLoadingInitial.value && controller.galleryCards.value.length === 0"
        class="page-card theme-section-muted text-sm"
      >
        {{ controller.isSetupStep.value ? 'No hero cards found for the current search.' : 'No cards found for the current filters.' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watchEffect, ref } from 'vue';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const sentinelRef = ref<HTMLElement | null>(null);

watchEffect(() => {
  props.controller.loadMoreSentinelRef.value = sentinelRef.value;
});
</script>
