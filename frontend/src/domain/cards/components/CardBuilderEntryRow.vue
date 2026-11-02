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
      v-if="reorderable !== false"
      class="deck-board-entry-drag-handle theme-card-frame-muted theme-section-muted theme-divider relative z-20 flex h-full w-8 shrink-0 cursor-grab items-center justify-center border-r opacity-75 transition hover:opacity-100 active:cursor-grabbing"
      type="button"
      aria-label="Drag to reorder card"
      title="Drag to reorder card"
      :disabled="mutationDisabled"
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
            :disabled="mutationDisabled || entry.quantity <= 1"
            aria-label="Remove one copy"
            @click.stop="handleDecrementClick"
            @contextmenu.stop
          >
            -
          </button>
          <button
            class="theme-divider inline-flex h-8 w-8 items-center justify-center border-l text-sm font-semibold transition hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
            type="button"
            :disabled="
              mutationDisabled || (quantityMax !== undefined && entry.quantity >= quantityMax)
            "
            aria-label="Add one copy"
            @click.stop="handleIncrementClick"
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
            class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-lg transition"
            aria-label="Move card to another board"
            title="Move card to another board"
            :disabled="mutationDisabled || singleMoveDestination?.disabled"
            @click.stop="handleMoveAction"
            @contextmenu.stop
          >
            <ArrowRightLeft class="h-4 w-4" />
          </button>

          <Teleport to="body">
            <div
              v-if="moveMenuOpen && moveDestinations.length > 1 && !mutationDisabled"
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
                    :disabled="mutationDisabled || destination.disabled"
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
          :disabled="mutationDisabled"
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

    <CardRowHoverPreview
      :anchor="triggerRef"
      :card="entry.card"
      :hover-mode="hoverMode"
      :active="hovered"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { ArrowRightLeft, GripVertical, Trash2 } from 'lucide-vue-next';
import CardCompactRowContent from '@/domain/cards/components/CardCompactRowContent.vue';
import CardRowHoverPreview from '@/domain/cards/components/CardRowHoverPreview.vue';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import type {
  CardBuilderEntry,
  CardBuilderMoveDestination,
} from '@/domain/cards/types/cardBuilder';
import {
  blurAfterFinePointerActivation,
  blurFocusedDescendantAfterFinePointerLeave,
} from '@/shared/utils/pointerFocus';

const props = withDefaults(
  defineProps<{
    entry: CardBuilderEntry;
    sortableCardId: string;
    reorderable?: boolean;
    hoverMode: HoverMode;
    quantityMax?: number;
    moveDestinations: CardBuilderMoveDestination[];
    mutationDisabled?: boolean;
    rowActionDisabled?: boolean;
    rowSecondaryActionDisabled?: boolean;
  }>(),
  { reorderable: true, quantityMax: undefined },
);

const emit = defineEmits<{
  (e: 'decrement', cardId: string): void;
  (e: 'increment', cardId: string): void;
  (e: 'remove', cardId: string): void;
  (e: 'row-action', cardId: string): void;
  (e: 'row-secondary-action', cardId: string): void;
  (e: 'move-to-board', cardId: string, destinationBoardId: string): void;
}>();

const hovered = ref(false);
const focusedWithin = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
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
const rowClickable = computed(
  () => !props.mutationDisabled && (!props.rowActionDisabled || !props.rowSecondaryActionDisabled),
);
const controlsVisible = computed(() => hovered.value || focusedWithin.value || moveMenuOpen.value);
const singleMoveDestination = computed(() =>
  props.moveDestinations.length === 1 ? props.moveDestinations[0] : null,
);
const rowQuantityWidth = '2.25rem';
const rowControlsRightOffset = `calc(${rowQuantityWidth} + 0.25rem)`;

const handleRowClick = (): void => {
  if (props.mutationDisabled || props.rowActionDisabled) {
    return;
  }
  emit('row-action', props.entry.card.id);
};

const handleRowKeydown = (): void => {
  if (props.mutationDisabled || props.rowActionDisabled) {
    return;
  }
  emit('row-action', props.entry.card.id);
};

const handleDecrementClick = (event: MouseEvent): void => {
  if (props.mutationDisabled) {
    return;
  }
  emit('decrement', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleIncrementClick = (event: MouseEvent): void => {
  if (props.mutationDisabled) {
    return;
  }
  emit('increment', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleRemoveClick = (event: MouseEvent): void => {
  if (props.mutationDisabled) {
    return;
  }
  emit('remove', props.entry.card.id);
  blurAfterFinePointerActivation(event);
};

const handleContextMenu = (event: MouseEvent): void => {
  event.preventDefault();
  if (props.mutationDisabled || props.rowSecondaryActionDisabled) {
    return;
  }
  emit('row-secondary-action', props.entry.card.id);
};

const handleMoveToBoard = (destinationBoardId: string): void => {
  if (props.mutationDisabled) {
    return;
  }
  emit('move-to-board', props.entry.card.id, destinationBoardId);
  closeMoveMenu();
};

const handleMoveAction = (): void => {
  if (props.mutationDisabled) {
    return;
  }
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

watch(
  () => props.mutationDisabled,
  (disabled) => {
    if (disabled) {
      closeMoveMenu();
    }
  },
);
</script>
