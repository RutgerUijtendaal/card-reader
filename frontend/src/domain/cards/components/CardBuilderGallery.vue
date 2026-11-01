<template>
  <div>
    <div class="space-y-6">
      <div
        class="grid gap-6 px-1 pb-3 pt-2"
        :style="gallery.galleryGridStyle.value"
      >
        <CardGalleryItem
          v-for="card in displayItems"
          :key="card.id"
          class="justify-self-center"
          :class="{
            'rounded-2xl ring-2 ring-[var(--accent)] ring-offset-2 ring-offset-[var(--color-surface)]':
              card.result_type !== 'loading_shim' && isSelected(card),
          }"
          :style="{
            width: `${gallery.galleryTileWidthRem.value}rem`,
            maxWidth: '100%',
          }"
          :card="card"
          :hover-mode="hoverMode"
          :card-height-rem="gallery.cardHeightRem.value"
          activation-mode="emit"
          :activation-label="card.result_type === 'loading_shim' ? 'Loading' : actionLabel(card)"
          :activation-disabled="card.result_type === 'loading_shim' || actionDisabled(card)"
          @activate="handleActivate"
          @contextmenu="handleContextMenu($event, card)"
        >
          <template #overlay>
            <div
              v-if="!selectionMode && card.result_type === 'card'"
              class="absolute inset-x-3 bottom-3 flex items-center justify-between gap-3"
            >
              <DeckCardCountBadge
                :quantity="getEntryQuantity(card.id)"
                :hide-when-zero="true"
              />
              <div v-if="getEntryQuantity(card.id) === 0" />

              <div
                class="pointer-events-none flex items-center gap-2 opacity-0 transition duration-200 group-hover:pointer-events-auto group-hover:opacity-100"
              >
                <button
                  class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold disabled:cursor-not-allowed disabled:border-[color:var(--color-disabled-border)] disabled:bg-[color:var(--color-disabled-bg)] disabled:text-[color:var(--color-disabled-text)] disabled:opacity-100"
                  type="button"
                  :disabled="removeDisabled(card.id)"
                  :aria-label="`Remove copy from ${collectionLabel}`"
                  @click.stop="removeCopy($event, card.id)"
                >
                  <Minus class="h-4 w-4" />
                </button>
                <button
                  class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold disabled:cursor-not-allowed disabled:border-[color:var(--color-disabled-border)] disabled:bg-[color:var(--color-disabled-bg)] disabled:text-[color:var(--color-disabled-text)] disabled:opacity-100"
                  type="button"
                  :disabled="actionDisabled(card)"
                  :aria-label="`Add copy to ${collectionLabel}`"
                  @click.stop="addCopy($event, card)"
                >
                  <Plus class="h-4 w-4" />
                </button>
              </div>
            </div>
          </template>
        </CardGalleryItem>
      </div>

      <div
        v-if="
          gallery.hasLoadedOnce.value &&
            !gallery.isRefreshing.value &&
            gallery.galleryCards.value.length > 0
        "
        ref="sentinelRef"
        class="theme-section-muted flex justify-center py-4 text-sm"
      >
        <span v-if="gallery.isLoadingPage.value">Loading more cards...</span>
        <span v-else-if="gallery.nextPage.value === null">All cards loaded.</span>
        <span v-else>Scroll to load more.</span>
      </div>

      <div
        v-if="
          gallery.hasLoadedOnce.value &&
            !gallery.isLoadingInitial.value &&
            !gallery.isRefreshing.value &&
            gallery.galleryCards.value.length === 0
        "
        class="page-card theme-section-muted text-sm"
      >
        {{ emptyMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watchEffect, ref } from 'vue';
import { Minus, Plus } from 'lucide-vue-next';
import CardGalleryItem from '@/domain/cards/components/CardGalleryItem.vue';
import {
  createLoadingShimItems,
  type GalleryDisplayItem,
} from '@/domain/cards/utils/galleryDisplayItems';
import type { GalleryItem } from '@/domain/cards/types';
import DeckCardCountBadge from '@/domain/cards/components/CardCountBadge.vue';
import type { CardBuilderGalleryState } from '@/domain/cards/types/cardBuilder';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { blurAfterFinePointerActivation } from '@/shared/utils/pointerFocus';

const props = withDefaults(
  defineProps<{
    gallery: CardBuilderGalleryState;
    hoverMode: HoverMode;
    selectionMode: boolean;
    isSelected: (card: GalleryItem) => boolean;
    actionLabel: (card: GalleryItem) => string;
    actionDisabled: (card: GalleryItem) => boolean;
    removeDisabled: (id: string) => boolean;
    quantity: (id: string) => number;
    activate: (card: GalleryItem) => void;
    remove: (id: string) => void;
    emptyMessage: string;
    collectionLabel?: string;
    loading?: boolean;
  }>(),
  {
    loading: false,
    collectionLabel: 'deck',
  },
);

const sentinelRef = ref<HTMLElement | null>(null);
const displayItems = computed(() =>
  props.loading || !props.gallery.hasLoadedOnce.value || props.gallery.isRefreshing.value
    ? createLoadingShimItems(props.gallery.loadingShimCount.value)
    : props.gallery.galleryCards.value,
);

const handleActivate = (card: GalleryItem): void => {
  props.activate(card);
};

const getEntryQuantity = (cardId: string): number => props.quantity(cardId);

const addCopy = (event: MouseEvent, card: GalleryItem): void => {
  props.activate(card);
  blurAfterFinePointerActivation(event);
};

const removeCopy = (event: MouseEvent, cardId: string): void => {
  props.remove(cardId);
  blurAfterFinePointerActivation(event);
};

const handleContextMenu = (event: MouseEvent, card: GalleryDisplayItem): void => {
  if (card.result_type !== 'card') {
    return;
  }

  event.preventDefault();
  if (props.removeDisabled(card.id)) {
    return;
  }
  props.remove(card.id);
};

watchEffect(() => {
  props.gallery.setLoadMoreSentinel(sentinelRef.value);
});
</script>
