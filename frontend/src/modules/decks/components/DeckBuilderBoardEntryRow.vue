<template>
  <div
    ref="triggerRef"
    :data-card-id="sortableCardId"
    class="theme-card-frame group relative flex h-[4.25rem] items-stretch overflow-hidden rounded-xl select-none"
    :class="rowClickable ? 'cursor-pointer' : 'cursor-default'"
    :tabindex="rowClickable ? 0 : undefined"
    @mouseenter="hovered = true"
    @mouseleave="handleMouseLeave"
    @focusin="focusedWithin = true"
    @focusout="handleFocusOut"
    @click="handleRowClick"
    @contextmenu="handleContextMenu"
    @keydown.enter.prevent="handleRowKeydown"
    @keydown.space.prevent="handleRowKeydown"
  >
    <button
      class="deck-board-entry-drag-handle theme-card-frame-muted theme-section-muted theme-divider relative z-20 flex h-full w-8 shrink-0 cursor-grab items-center justify-center border-r opacity-75 transition hover:opacity-100 active:cursor-grabbing"
      type="button"
      aria-label="Drag to reorder card"
      title="Drag to reorder card"
      @click.stop
      @contextmenu.stop
    >
      <GripVertical class="h-4 w-4" />
    </button>

    <CardCompactRowContent :card="entry.card" />

    <div
      v-if="controlsVisible"
      class="pointer-events-none absolute inset-y-0 z-20 flex items-center"
      :style="{ right: rowControlsRightOffset }"
    >
      <div class="pointer-events-auto flex items-center gap-2">
        <div
          class="theme-card-frame-muted inline-flex items-center overflow-hidden rounded-lg"
          data-testid="row-count-controls"
          @click.stop
          @contextmenu.stop
        >
          <button
            class="inline-flex h-8 w-8 items-center justify-center text-sm font-semibold transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            type="button"
            :disabled="entry.quantity <= 1"
            aria-label="Remove one copy"
            @click.stop="handleDecrementClick"
            @contextmenu.stop
          >
            -
          </button>
          <button
            class="theme-divider inline-flex h-8 w-8 items-center justify-center border-l text-sm font-semibold transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            type="button"
            :disabled="quantityMax !== undefined && entry.quantity >= quantityMax"
            aria-label="Add one copy"
            @click.stop="handleIncrementClick"
            @contextmenu.stop
          >
            +
          </button>
        </div>

        <div
          class="theme-card-frame-muted inline-flex items-center overflow-hidden rounded-lg"
          data-testid="row-reorder-controls"
          @click.stop
          @contextmenu.stop
        >
          <button
            class="inline-flex h-8 w-8 items-center justify-center transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            type="button"
            :disabled="!canReorderUp"
            aria-label="Move card up"
            @click.stop="handleReorderUpClick"
            @contextmenu.stop
          >
            <ArrowUp class="h-4 w-4" />
          </button>
          <button
            class="theme-divider inline-flex h-8 w-8 items-center justify-center border-l transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            type="button"
            :disabled="!canReorderDown"
            aria-label="Move card down"
            @click.stop="handleReorderDownClick"
            @contextmenu.stop
          >
            <ArrowDown class="h-4 w-4" />
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
            class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-lg transition"
            aria-label="Move card to another board"
            title="Move card to another board"
            :disabled="singleMoveDestination?.disabled"
            @click.stop="handleMoveAction"
            @contextmenu.stop
          >
            <ArrowRightLeft class="h-4 w-4" />
          </button>

          <Teleport to="body">
            <div
              v-if="moveMenuOpen && moveDestinations.length > 1"
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
          @click.stop="handleRemoveClick"
          @contextmenu.stop
        >
          <Trash2 class="h-4 w-4" />
        </button>
      </div>
    </div>

    <div
      class="theme-card-frame-muted theme-divider relative z-10 flex h-full w-9 shrink-0 items-center justify-center border-l"
      data-testid="row-quantity-badge"
    >
      <span class="theme-section-title text-sm font-semibold">
        {{ entry.quantity }}
      </span>
    </div>

    <Teleport to="body">
      <div
        v-if="sharedElementHover.isMounted.value"
        ref="hoverPanelRef"
        class="pointer-events-none z-30 hidden md:block"
        :class="sharedElementHover.overlayClass.value"
        :style="sharedElementHover.overlayStyle.value"
      >
        <CardHoverTooltip
          v-if="showEnlargedPreview && showDetailsPreview"
          :card="entry.card"
          :image-url="entry.card.image_url"
          :image-alt="entry.card.name"
          :details-revealed="sharedElementHover.revealDetails.value"
          :hover-preview-scale="hoverPreviewScale"
        />
        <div
          v-else-if="showEnlargedPreview && entry.card.image_url"
          class="theme-card-frame overflow-hidden rounded-xl shadow-2xl"
          :style="enlargedPreviewStyle"
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
          :details-revealed="sharedElementHover.revealDetails.value"
        />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, ref } from 'vue';
import { ArrowDown, ArrowRightLeft, ArrowUp, GripVertical, Trash2 } from 'lucide-vue-next';
import { toAbsoluteApiUrl } from '@/api/client';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import CardCompactRowContent from '@/components/cards/CardCompactRowContent.vue';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import type { HoverMode } from '@/composables/card-gallery/hoverMode';
import { normalizeHoverPreviewScale } from '@/composables/card-gallery/hoverPreviewScale';
import { useSharedElementHover } from '@/composables/card-gallery/useSharedElementHover';
import { useHoverModePreferences } from '@/composables/useHoverModePreferences';
import type { DeckEntrySummary } from '@/modules/decks/types';
import type { DeckBoardMoveDestination } from '@/modules/decks/composables/useDeckEditorDraft';
import { blurAfterFinePointerActivation, blurFocusedDescendantAfterFinePointerLeave } from '@/utils/pointerFocus';

const props = defineProps<{
  entry: DeckEntrySummary;
  sortableCardId: string;
  hoverMode: HoverMode;
  quantityMax?: number;
  moveDestinations: DeckBoardMoveDestination[];
  rowActionDisabled?: boolean;
  rowSecondaryActionDisabled?: boolean;
  canReorderUp?: boolean;
  canReorderDown?: boolean;
}>();

const emit = defineEmits<{
  (e: 'decrement', cardId: string): void;
  (e: 'increment', cardId: string): void;
  (e: 'remove', cardId: string): void;
  (e: 'row-action', cardId: string): void;
  (e: 'row-secondary-action', cardId: string): void;
  (e: 'move-to-board', cardId: string, destinationBoardId: string): void;
  (e: 'reorder-up', cardId: string): void;
  (e: 'reorder-down', cardId: string): void;
}>();

const hovered = ref(false);
const focusedWithin = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const hoverPanelRef = ref<HTMLElement | null>(null);
const { hoverPreviewScale } = useHoverModePreferences();
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
const BASE_HOVER_CARD_WIDTH_REM = 28;
const enlargedPreviewStyle = computed(() => ({
  width: `${Number((BASE_HOVER_CARD_WIDTH_REM * normalizeHoverPreviewScale(hoverPreviewScale.value)).toFixed(3))}rem`,
}));
const sharedElementHover = useSharedElementHover({
  isOpen: showHoverOverlay,
  panelRef: hoverPanelRef,
  triggerRef,
  x: hoverPanelX,
  y: hoverPanelY,
});
const rowClickable = computed(() => !props.rowActionDisabled || !props.rowSecondaryActionDisabled);
const controlsVisible = computed(() => hovered.value || focusedWithin.value || moveMenuOpen.value);
const singleMoveDestination = computed(() =>
  props.moveDestinations.length === 1 ? props.moveDestinations[0] : null,
);
const rowQuantityWidth = '2.25rem';
const rowControlsRightOffset = `calc(${rowQuantityWidth} + 0.25rem)`;

const handleRowClick = (): void => {
  if (props.rowActionDisabled) {
    return;
  }
  emit('row-action', props.entry.card.id);
};

const handleRowKeydown = (): void => {
  if (props.rowActionDisabled) {
    return;
  }
  emit('row-action', props.entry.card.id);
};

const handleDecrementClick = (event: MouseEvent): void => {
  emit('decrement', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleIncrementClick = (event: MouseEvent): void => {
  emit('increment', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleReorderUpClick = (event: MouseEvent): void => {
  emit('reorder-up', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleReorderDownClick = (event: MouseEvent): void => {
  emit('reorder-down', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleRemoveClick = (event: MouseEvent): void => {
  emit('remove', props.entry.card.id);
  blurAfterFinePointerActivation(event);
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

const handleMoveAction = (): void => {
  if (singleMoveDestination.value) {
    if (singleMoveDestination.value.disabled) {
      return;
    }
    handleMoveToBoard(singleMoveDestination.value.boardId);
    return;
  }
  toggleMoveMenu();
};

const handleFocusOut = (event: FocusEvent): void => {
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && triggerRef.value?.contains(nextTarget)) {
    return;
  }
  focusedWithin.value = false;
};

const handleMouseLeave = (): void => {
  hovered.value = false;
  blurFocusedDescendantAfterFinePointerLeave(triggerRef.value);
};
</script>
