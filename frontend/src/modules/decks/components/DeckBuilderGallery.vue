<template>
  <div class="app-scrollbar min-h-0 overflow-y-auto pr-1">
    <div class="space-y-6">
      <div
        class="grid gap-6 px-1 pb-3 pt-2"
        :style="controller.gallery.galleryGridStyle.value"
      >
        <CardGalleryItem
          v-for="card in displayItems"
          :key="card.id"
          class="justify-self-center"
          :style="{
            width: `${controller.gallery.galleryTileWidthRem.value}rem`,
            maxWidth: '100%',
          }"
          :card="card"
          :hover-mode="controller.filters.hoverMode.value"
          :card-height-rem="controller.gallery.cardHeightRem.value"
          activation-mode="emit"
          activation-label="Add card to deck"
          :activation-disabled="card.result_type !== 'card' || controller.deck.galleryActionDisabled(card)"
          @activate="handleActivate"
          @contextmenu="handleContextMenu($event, card)"
        >
          <template #overlay>
            <div
              v-if="!controller.deck.isSetupStep.value && card.result_type === 'card'"
              class="absolute inset-x-3 bottom-3 flex items-center justify-between gap-3"
            >
              <DeckCardCountBadge
                :quantity="getEntryQuantity(card.id)"
                :hide-when-zero="true"
              />
              <div v-if="getEntryQuantity(card.id) === 0" />

              <div class="pointer-events-none flex items-center gap-2 opacity-0 transition duration-200 group-hover:pointer-events-auto group-hover:opacity-100">
                <button
                  class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold disabled:cursor-not-allowed disabled:border-[color:var(--color-disabled-border)] disabled:bg-[color:var(--color-disabled-bg)] disabled:text-[color:var(--color-disabled-text)] disabled:opacity-100"
                  type="button"
                  :disabled="controller.deck.galleryRemoveActionDisabled(card.id)"
                  aria-label="Remove copy from deck"
                  @click.stop="removeCopy(card.id)"
                >
                  <Minus class="h-4 w-4" />
                </button>
                <button
                  class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold disabled:cursor-not-allowed disabled:border-[color:var(--color-disabled-border)] disabled:bg-[color:var(--color-disabled-bg)] disabled:text-[color:var(--color-disabled-text)] disabled:opacity-100"
                  type="button"
                  :disabled="controller.deck.galleryActionDisabled(card)"
                  aria-label="Add copy to deck"
                  @click.stop="addCopy(card)"
                >
                  <Plus class="h-4 w-4" />
                </button>
              </div>
            </div>
          </template>
        </CardGalleryItem>
      </div>

      <div
        v-if="controller.gallery.hasLoadedOnce.value && !controller.gallery.isRefreshing.value && controller.gallery.galleryCards.value.length > 0"
        ref="sentinelRef"
        class="theme-section-muted flex justify-center py-4 text-sm"
      >
        <span v-if="controller.gallery.isLoadingPage.value">Loading more cards...</span>
        <span v-else-if="controller.gallery.nextPage.value === null">All cards loaded.</span>
        <span v-else>Scroll to load more.</span>
      </div>

      <div
        v-if="controller.gallery.hasLoadedOnce.value && !controller.gallery.isLoadingInitial.value && !controller.gallery.isRefreshing.value && controller.gallery.galleryCards.value.length === 0"
        class="page-card theme-section-muted text-sm"
      >
        {{ controller.deck.isSetupStep.value ? 'No hero cards found for the current search.' : 'No cards found for the current filters.' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watchEffect, ref } from 'vue';
import { Minus, Plus } from 'lucide-vue-next';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import { createLoadingShimItems, type GalleryDisplayItem } from '@/components/cards/galleryDisplayItems';
import type { GalleryItem } from '@/modules/card-detail/types';
import DeckCardCountBadge from '@/modules/decks/components/DeckCardCountBadge.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const sentinelRef = ref<HTMLElement | null>(null);
const displayItems = computed(() =>
  (!props.controller.gallery.hasLoadedOnce.value || props.controller.gallery.isRefreshing.value)
    ? createLoadingShimItems(props.controller.gallery.loadingShimCount.value)
    : props.controller.gallery.galleryCards.value,
);

const handleActivate = (card: GalleryItem): void => {
  if (card.result_type !== 'card') {
    return;
  }
  props.controller.deck.handleGalleryAction(card);
};

const getEntryQuantity = (cardId: string): number =>
  props.controller.deck.getEntryQuantity(cardId);

const addCopy = (card: GalleryItem): void => {
  if (card.result_type !== 'card') {
    return;
  }
  props.controller.deck.handleGalleryAction(card);
};

const removeCopy = (cardId: string): void => {
  props.controller.deck.handleGalleryRemoveAction(cardId);
};

const handleContextMenu = (event: MouseEvent, card: GalleryDisplayItem): void => {
  if (card.result_type !== 'card' || props.controller.deck.galleryRemoveActionDisabled(card.id)) {
    return;
  }

  event.preventDefault();
  props.controller.deck.handleGalleryRemoveAction(card.id);
};

watchEffect(() => {
  props.controller.gallery.setLoadMoreSentinel(sentinelRef.value);
});
</script>
