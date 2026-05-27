<template>
  <div
    ref="triggerRef"
    class="theme-card-frame group flex items-center gap-2 rounded-2xl px-3 py-2 select-none"
    :class="rowClickable ? 'cursor-pointer' : 'cursor-default'"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
    @click="handleRowClick"
    @contextmenu="handleContextMenu"
  >
    <div class="min-w-0 flex-1 select-none">
      <p class="theme-section-title truncate text-sm font-semibold">
        {{ entry.card.name }}
      </p>
    </div>

    <div
      class="theme-card-frame-muted inline-flex items-center overflow-hidden rounded-lg"
      @click.stop
      @contextmenu.stop
    >
      <button
        class="inline-flex h-8 w-7 items-center justify-center text-xs font-semibold transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
        type="button"
        :disabled="entry.quantity <= 1"
        aria-label="Remove one copy"
        @click.stop="$emit('decrement', entry.card.id)"
        @contextmenu.stop
      >
        -
      </button>
      <span class="theme-divider inline-flex h-8 min-w-9 items-center justify-center border-x px-2 text-xs font-semibold">
        {{ entry.quantity }}
      </span>
      <button
        class="inline-flex h-8 w-7 items-center justify-center text-xs font-semibold transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
        type="button"
        :disabled="quantityMax !== undefined && entry.quantity >= quantityMax"
        aria-label="Add one copy"
        @click.stop="$emit('increment', entry.card.id)"
        @contextmenu.stop
      >
        +
      </button>
    </div>

    <div
      v-if="moveDestinations.length > 0"
      class="relative"
      @click.stop
      @contextmenu.stop
    >
      <button
        ref="moveTriggerRef"
        type="button"
        class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-lg"
        aria-label="Move card to another board"
        title="Move card to another board"
        @click.stop="toggleMoveMenu"
        @contextmenu.stop
      >
        <ArrowRightLeft class="h-4 w-4" />
      </button>

      <Teleport to="body">
        <div
          v-if="moveMenuOpen"
          ref="movePanelRef"
          class="theme-popover z-40 w-[15rem] p-3"
          :style="{ position: 'fixed', left: `${moveMenuX}px`, top: `${moveMenuY}px` }"
        >
          <div class="space-y-2">
            <p class="theme-section-title text-sm font-semibold">
              Move To Board
            </p>
            <div class="theme-panel-shell overflow-hidden">
              <button
                v-for="destination in moveDestinations"
                :key="destination.boardId"
                type="button"
                class="theme-divider w-full border-t px-3 py-2 text-left first:border-t-0 disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="destination.disabled"
                @click.stop="handleMoveToBoard(destination.boardId)"
              >
                <p class="theme-section-title text-sm font-semibold">
                  {{ destination.label }}
                </p>
                <p
                  v-if="destination.description"
                  class="theme-section-muted mt-1 text-xs"
                >
                  {{ destination.description }}
                </p>
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </div>

    <button
      class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition hover:text-rose-300"
      type="button"
      aria-label="Remove card from board"
      @click.stop="$emit('remove', entry.card.id)"
      @contextmenu.stop
    >
      <Trash2 class="h-4 w-4" />
    </button>

    <Teleport to="body">
      <div
        v-if="showHoverOverlay"
        ref="hoverPanelRef"
        class="pointer-events-none z-30 hidden md:block"
        :style="{ position: 'fixed', left: `${hoverPanelX}px`, top: `${hoverPanelY}px` }"
      >
        <CardHoverTooltip
          v-if="showEnlargedPreview && showDetailsPreview"
          :card="entry.card"
          :image-url="entry.card.image_url"
          :image-alt="entry.card.name"
        />
        <div
          v-else-if="showEnlargedPreview && entry.card.image_url"
          class="theme-card-frame w-[28rem] overflow-hidden rounded-xl shadow-2xl"
        >
          <div class="theme-card-image-well aspect-[63/88]">
            <img
              :src="toAbsoluteApiUrl(entry.card.image_url)"
              :alt="entry.card.name"
              class="h-full w-full object-cover"
            >
          </div>
        </div>
        <CardHoverTooltip
          v-else-if="showDetailsPreview"
          :card="entry.card"
        />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref } from 'vue';
import { ArrowRightLeft, Trash2 } from 'lucide-vue-next';
import { toAbsoluteApiUrl } from '@/api/client';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import type { HoverMode } from '@/modules/card-search/hoverMode';
import type { DeckEntrySummary } from '@/modules/decks/types';
import type { DeckBoardMoveDestination } from '@/modules/decks/composables/useDeckEditorDraft';

const props = defineProps<{
  entry: DeckEntrySummary;
  hoverMode: HoverMode;
  quantityMax?: number;
  moveDestinations: DeckBoardMoveDestination[];
  rowActionDisabled?: boolean;
  rowSecondaryActionDisabled?: boolean;
}>();

const emit = defineEmits<{
  (e: 'decrement', cardId: string): void;
  (e: 'increment', cardId: string): void;
  (e: 'remove', cardId: string): void;
  (e: 'row-action', cardId: string): void;
  (e: 'row-secondary-action', cardId: string): void;
  (e: 'move-to-board', cardId: string, destinationBoardId: string): void;
}>();

const hovered = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const hoverPanelRef = ref<HTMLElement | null>(null);
const {
  isOpen: moveMenuOpen,
  triggerRef: moveTriggerRef,
  panelRef: movePanelRef,
  x: moveMenuX,
  y: moveMenuY,
  toggle: toggleMoveMenu,
  close: closeMoveMenu,
} = useFloatingPopover({
  placement: 'bottom-end',
});
const showEnlargedPreview = computed(() => props.hoverMode === 'enlarged' || props.hoverMode === 'enlarged-details');
const showDetailsPreview = computed(() => props.hoverMode === 'details' || props.hoverMode === 'enlarged-details');
const showHoverOverlay = computed(() => {
  if (!hovered.value || props.hoverMode === 'none') {
    return false;
  }

  return (showEnlargedPreview.value && props.entry.card.image_url !== null) || showDetailsPreview.value;
});
const floating = useFloating(triggerRef, hoverPanelRef, {
  open: showHoverOverlay,
  placement: 'left-start',
  strategy: 'fixed',
  middleware: [offset(16), flip(), shift({ padding: 12 })],
  whileElementsMounted: autoUpdate,
});
const hoverPanelX = computed(() => floating.x.value ?? 0);
const hoverPanelY = computed(() => floating.y.value ?? 0);
const rowClickable = computed(() => !props.rowActionDisabled || !props.rowSecondaryActionDisabled);

const handleRowClick = (): void => {
  if (props.rowActionDisabled) {
    return;
  }
  emit('row-action', props.entry.card.id);
};

const handleContextMenu = (event: MouseEvent): void => {
  event.preventDefault();
  if (props.rowSecondaryActionDisabled) {
    return;
  }
  emit('row-secondary-action', props.entry.card.id);
};

const handleMoveToBoard = (destinationBoardId: string): void => {
  emit('move-to-board', props.entry.card.id, destinationBoardId);
  closeMoveMenu();
};
</script>
