<template>
  <div
    ref="triggerRef"
    class="theme-card-frame group relative flex items-stretch overflow-hidden rounded-xl select-none"
    :class="rowClickable ? 'cursor-pointer' : 'cursor-default'"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
    @focusin="focusedWithin = true"
    @focusout="handleFocusOut"
    @click="handleRowClick"
    @contextmenu="handleContextMenu"
  >
    <div class="theme-card-frame-muted theme-divider relative z-10 flex w-11 shrink-0 items-center justify-center border-r">
      <span class="theme-section-title text-sm font-semibold">
        {{ manaBadgeLabel }}
      </span>
    </div>

    <div class="relative z-10 min-w-0 flex-1 overflow-hidden px-3 py-2">
      <div class="flex min-h-10 items-center gap-3 pr-2">
        <div class="min-w-0 flex-1 select-none">
          <p class="theme-section-title truncate text-sm font-semibold">
            {{ entry.card.name }}
          </p>
        </div>

        <div
          v-if="controlsVisible"
          class="flex items-center gap-1"
        >
          <div
            class="theme-card-frame-muted inline-flex items-center overflow-hidden rounded-lg"
            data-testid="row-count-controls"
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
              class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-8 w-8 items-center justify-center rounded-lg transition"
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
        </div>
      </div>
    </div>

    <div
      v-if="entry.card.image_url"
      class="pointer-events-none absolute inset-y-0 right-0 w-24 overflow-hidden"
    >
      <img
        :src="toAbsoluteApiUrl(entry.card.image_url)"
        :alt="entry.card.name"
        class="h-full w-full object-cover opacity-95"
        :style="{ objectPosition: rowArtObjectPosition }"
      >
      <div
        class="absolute inset-y-0 left-0 w-[12%]"
        style="background: linear-gradient(to right, var(--color-surface-strong) 0%, color-mix(in srgb, var(--color-surface-strong) 78%, transparent 22%) 45%, transparent 100%);"
      />
      <div class="absolute inset-0 bg-gradient-to-l from-slate-950/70 via-slate-950/30 to-transparent" />
    </div>
    <div
      v-else
      class="pointer-events-none absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-slate-800/35 via-slate-700/12 to-transparent"
    />

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
const focusedWithin = ref(false);
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
const manaBadgeLabel = computed(() => props.entry.card.mana_value === null ? '—' : String(props.entry.card.mana_value));
const controlsVisible = computed(() => hovered.value || focusedWithin.value || moveMenuOpen.value);
const rowArtObjectPosition = 'center 20%';

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

const handleFocusOut = (event: FocusEvent): void => {
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && triggerRef.value?.contains(nextTarget)) {
    return;
  }
  focusedWithin.value = false;
};
</script>
