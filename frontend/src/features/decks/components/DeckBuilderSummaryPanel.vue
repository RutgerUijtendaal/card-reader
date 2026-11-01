<template>
  <aside
    class="app-sticky-aside app-sticky-aside-right page-card flex min-h-0 flex-col overflow-hidden p-0"
  >
    <div
      class="z-20 space-y-3"
      data-testid="deck-summary-top"
    >
      <section
        ref="heroDetailsTriggerRef"
        class="overflow-hidden"
      >
        <CardBuilderSummaryHeader
          :name="controller.deck.form.name || 'Untitled Deck'"
          :card="controller.deck.selectedHero.value"
          :board-label="activeBoardLabel"
          :count="activeBoardCount"
          empty-label="Choose hero"
          :action-label="
            controller.deck.selectedHero.value
              ? heroDetailsExpanded
                ? 'Collapse hero details'
                : 'Expand hero details'
              : 'Choose hero'
          "
          :expanded="heroDetailsExpanded"
          :object-position="heroHeaderObjectPosition"
          :image-transform="heroHeaderTransform"
          :image-opacity="heroHeaderOpacity"
          @activate="handleHeroHeaderClick()"
        />
      </section>

      <BuilderPanelTabs
        class="!mt-0"
        label="Deck builder view"
        :tabs="viewTabs"
        :disabled="controller.isMutationLocked.value"
        @select="selectView"
      />

      <CardBuilderBoards
        :active-board-id="controller.deck.activeBoardId.value"
        :mainboard-count="controller.deck.totalMainboardCards.value"
        :sideboards="controller.deck.sideboardTabs.value"
        :locked="controller.isMutationLocked.value"
        @add="controller.deck.addSideboard()"
        @select="controller.deck.selectBoard"
        @rename="controller.deck.renameSideboard"
        @remove="controller.deck.removeSideboard"
      />
    </div>

    <Teleport to="body">
      <div
        v-if="heroDetailsExpanded"
        ref="heroDetailsPanelRef"
        class="theme-popover z-30 p-4"
        data-testid="deck-summary-hero-details"
        :style="{
          position: 'fixed',
          left: `${heroDetailsX}px`,
          top: `${heroDetailsY}px`,
          width: `${heroDetailsPanelWidth}px`,
        }"
      >
        <div class="space-y-4">
          <div
            v-if="controller.deck.selectedHero.value?.image_url"
            class="theme-card-frame-muted mx-auto w-full max-w-[22rem] overflow-hidden rounded-xl"
          >
            <img
              :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
              :alt="controller.deck.selectedHero.value.name"
              class="h-full w-full object-cover object-top"
            >
          </div>
          <div
            v-else
            class="theme-empty-state mx-auto flex h-[31rem] w-full max-w-[22rem] items-center justify-center rounded-xl text-sm"
          >
            No hero
          </div>

          <div class="theme-divider border-t" />

          <DeckManaCurve
            :entries="controller.deck.detailedMainboardEntries.value"
            empty-label="Add mainboard cards to see the mana curve."
            compact
            title=""
          />
        </div>
      </div>
    </Teleport>

    <div
      ref="boardListRef"
      class="app-scrollbar relative z-10 mt-4 flex-1 min-h-0 overflow-y-auto overscroll-contain px-5 pb-5 pr-4"
      data-testid="deck-summary-list"
    >
      <div
        ref="boardEntriesSortableRef"
        class="space-y-3 pb-1"
      >
        <div
          v-if="controller.deck.detailedActiveBoardEntries.value.length === 0"
          class="theme-empty-state"
        >
          No cards added to this board yet.
        </div>

        <DeckBuilderBoardEntryRow
          v-for="entry in controller.deck.detailedActiveBoardEntries.value"
          :key="entry.card.id"
          :ref="(element) => setBoardEntryRowRef(entry.card.id, element)"
          :entry="entry"
          :sortable-card-id="entry.card.id"
          :hover-mode="controller.filters.hoverMode.value"
          :class="{ 'deck-board-entry-pop': poppedBoardEntryCardId === entry.card.id }"
          :quantity-max="controller.deck.getCardQuantityLimit(entry.card.id)"
          :move-destinations="getMoveDestinations(entry.card.id)"
          :mutation-disabled="controller.isMutationLocked.value"
          :row-action-disabled="controller.deck.boardRowActionDisabled(entry.card.id)"
          :row-secondary-action-disabled="
            controller.deck.boardRowSecondaryActionDisabled(entry.card.id)
          "
          @decrement="controller.deck.changeQuantity($event, -1)"
          @increment="controller.deck.changeQuantity($event, 1)"
          @remove="controller.deck.removeEntry"
          @row-action="controller.deck.handleBoardRowAction"
          @row-secondary-action="controller.deck.handleBoardRowSecondaryAction"
          @move-to-board="handleMoveToBoard"
        />
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useSortable } from '@vueuse/integrations/useSortable';
import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
import { Crown, FileText, LayoutGrid } from 'lucide-vue-next';
import BuilderPanelTabs from '@/shared/components/builders/BuilderPanelTabs.vue';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';
import CardBuilderBoards from '@/domain/cards/components/CardBuilderBoards.vue';
import CardBuilderSummaryHeader from '@/domain/cards/components/CardBuilderSummaryHeader.vue';
import DeckBuilderBoardEntryRow from '@/domain/cards/components/CardBuilderEntryRow.vue';
import DeckManaCurve from '@/features/decks/components/DeckManaCurve.vue';
import type { DeckEditorController } from '@/features/decks/composables/useDeckEditor';
import type { DeckBoardMoveDestination } from '@/features/decks/composables/deckEditorDraftTypes';
import type { DeckEntrySummary } from '@/domain/decks/types';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const {
  isOpen: heroDetailsExpanded,
  triggerRef: heroDetailsTriggerRef,
  panelRef: heroDetailsPanelRef,
  x: heroDetailsX,
  y: heroDetailsY,
  toggle: toggleHeroDetails,
} = useFloatingPopover({
  placement: 'bottom-start',
});
const heroDetailsPanelWidth = computed(() => heroDetailsTriggerRef.value?.offsetWidth ?? 0);
const boardListRef = ref<HTMLElement | null>(null);
const boardEntriesSortableRef = ref<HTMLElement | null>(null);
const sortableEntries = shallowRef<DeckEntrySummary[]>([]);
const boardEntryRowRefs = new Map<string, HTMLElement>();
const poppedBoardEntryCardId = ref<string | null>(null);
let popResetTimer: number | undefined;

const sortableController = useSortable(boardEntriesSortableRef, sortableEntries, {
  animation: 160,
  handle: '.deck-board-entry-drag-handle',
  ghostClass: 'deck-board-entry-sortable-ghost',
  chosenClass: 'deck-board-entry-sortable-chosen',
  dragClass: 'deck-board-entry-sortable-drag',
  scroll: true,
  forceAutoScrollFallback: true,
  bubbleScroll: false,
  scrollSensitivity: 180,
  scrollSpeed: 18,
  watchElement: true,
  onStart: (): void => {
    sortableController.option('scroll', boardListRef.value ?? true);
    sortableController.option('bubbleScroll', false);
  },
  onEnd: (): void => {
    sortableController.option('scroll', boardListRef.value ?? true);
    sortableController.option('bubbleScroll', false);
  },
  onUpdate: (event: { item: HTMLElement; newIndex?: number }): void => {
    if (props.controller.isMutationLocked.value) {
      return;
    }
    const movedCardId = event.item.dataset.cardId;
    if (!movedCardId || event.newIndex === undefined) {
      return;
    }
    props.controller.deck.moveEntryToIndex(
      props.controller.deck.activeBoardId.value,
      movedCardId,
      event.newIndex,
    );
  },
});

watch(
  boardListRef,
  (listElement) => {
    sortableController.option('scroll', listElement ?? true);
    sortableController.option('bubbleScroll', false);
  },
  { immediate: true },
);

const componentRefElement = (element: unknown): HTMLElement | null => {
  if (element instanceof HTMLElement) {
    return element;
  }
  if (
    element !== null &&
    typeof element === 'object' &&
    '$el' in element &&
    element.$el instanceof HTMLElement
  ) {
    return element.$el;
  }
  return null;
};

const setBoardEntryRowRef = (cardId: string, element: unknown): void => {
  const rowElement = componentRefElement(element);
  if (rowElement) {
    boardEntryRowRefs.set(cardId, rowElement);
    return;
  }
  boardEntryRowRefs.delete(cardId);
};

const scrollBoardEntryIntoView = (rowElement: HTMLElement): void => {
  const listElement = boardListRef.value;
  if (!listElement) {
    return;
  }

  const listRect = listElement.getBoundingClientRect();
  const rowRect = rowElement.getBoundingClientRect();
  const isFullyVisible = rowRect.top >= listRect.top && rowRect.bottom <= listRect.bottom;
  if (isFullyVisible) {
    return;
  }

  const nextScrollTop =
    rowElement.offsetTop - listElement.clientHeight / 2 + rowElement.clientHeight / 2;
  listElement.scrollTo({
    top: Math.max(0, nextScrollTop),
    behavior: 'smooth',
  });
};

const activeBoardLabel = computed(() =>
  props.controller.deck.activeBoardId.value === 'mainboard'
    ? 'Mainboard'
    : props.controller.deck.activeSideboard.value?.name.trim() || 'Sideboard',
);
const activeBoardCount = computed(() =>
  props.controller.deck.activeBoardId.value === 'mainboard'
    ? props.controller.deck.totalMainboardCards.value
    : (props.controller.deck.activeSideboard.value?.entries.reduce(
        (sum, entry) => sum + entry.quantity,
        0,
      ) ?? 0),
);
const heroHeaderObjectPosition = '30% 10%';
const heroHeaderTransform = 'scale(1.28)';
const heroHeaderOpacity = 0.75;
type DeckBuilderView = 'cards' | 'hero' | 'details';

const viewTabs = computed(() => {
  const detailsOpen = props.controller.detailsOpen.value;
  const mode = props.controller.editorMode.value;
  return [
    { id: 'hero' as const, label: 'Hero', icon: Crown, active: !detailsOpen && mode === 'hero' },
    { id: 'cards' as const, label: 'Cards', icon: LayoutGrid, active: !detailsOpen && mode === 'cards' },
    { id: 'details' as const, label: 'Details', icon: FileText, active: detailsOpen },
  ];
});

const selectView = (view: DeckBuilderView): void => {
  if (view === 'cards') {
    props.controller.openCards();
  } else if (view === 'hero') {
    props.controller.openHero();
  } else {
    props.controller.openDetails();
  }
};

const handleHeroHeaderClick = (): void => {
  if (!props.controller.deck.selectedHero.value) {
    props.controller.openHero();
    return;
  }
  toggleHeroDetails();
};

watch(
  () => props.controller.deck.lastBoardEntryChange.value?.sequence,
  async () => {
    const change = props.controller.deck.lastBoardEntryChange.value;
    if (!change || change.boardId !== props.controller.deck.activeBoardId.value) {
      return;
    }

    await nextTick();
    const rowElement = boardEntryRowRefs.get(change.cardId);
    if (!rowElement) {
      return;
    }

    scrollBoardEntryIntoView(rowElement);
    poppedBoardEntryCardId.value = null;
    await nextTick();
    poppedBoardEntryCardId.value = change.cardId;
    if (popResetTimer !== undefined) {
      window.clearTimeout(popResetTimer);
    }
    popResetTimer = window.setTimeout(() => {
      poppedBoardEntryCardId.value = null;
      popResetTimer = undefined;
    }, 320);
  },
);

watch(
  () => props.controller.deck.detailedActiveBoardEntries.value,
  (entries) => {
    sortableEntries.value = [...entries];
    void nextTick(() => {
      sortableController.option(
        'disabled',
        props.controller.isMutationLocked.value || entries.length < 2,
      );
    });
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  if (popResetTimer !== undefined) {
    window.clearTimeout(popResetTimer);
  }
});

const getMoveDestinations = (cardId: string): DeckBoardMoveDestination[] =>
  props.controller.deck.getBoardMoveDestinations(cardId);

const handleMoveToBoard = (cardId: string, destinationBoardId: string): void => {
  if (props.controller.isMutationLocked.value) {
    return;
  }
  props.controller.deck.moveEntryToBoard(cardId, destinationBoardId);
};

watch(
  () => props.controller.isMutationLocked.value,
  (creating) => {
    sortableController.option(
      'disabled',
      creating || props.controller.deck.detailedActiveBoardEntries.value.length < 2,
    );
    if (!creating) {
      return;
    }
  },
);
</script>

<style scoped>
.deck-board-entry-pop {
  animation: deck-board-entry-pop 320ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.deck-board-entry-sortable-ghost {
  opacity: 0.35;
}

.deck-board-entry-sortable-chosen {
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 42%, transparent);
}

.deck-board-entry-sortable-drag {
  opacity: 0.92;
  box-shadow: 0 18px 36px rgb(15 23 42 / 0.24);
}

@keyframes deck-board-entry-pop {
  0% {
    transform: scale(1);
  }

  38% {
    transform: scale(1.035);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent) 42%, transparent);
  }

  100% {
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .deck-board-entry-pop {
    animation: none;
  }
}
</style>
