<template>
  <section
    class="playtester-page flex flex-col"
    :class="isPreSetupStage ? 'playtester-page-pre-setup' : ''"
  >
    <AppPageHeader
      :icon="Gamepad2"
      :title="pageTitle"
      :subtitle="pageSubtitle"
      :back-to="isPreSetupStage ? null : '/playtester'"
      :back-label="isPreSetupStage ? '' : 'Back to Playtester'"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <RouterLink
          v-if="!isPreSetupStage && deck"
          class="btn-secondary"
          :to="`/decks/${deck.id}`"
        >
          Deck Detail
        </RouterLink>
      </template>
    </AppPageHeader>

    <div
      v-if="!isPreSetupStage && activeDeckLoading"
      class="playtester-loading theme-card-frame-muted"
      aria-label="Loading playtester"
    />

    <div
      v-else-if="!isPreSetupStage && (!deck || !playtest)"
      class="theme-empty-state text-sm"
    >
      Deck not found.
    </div>

    <PlaytestPreSetupStage
      v-else-if="isPreSetupStage"
      v-model:search-query="deckSelection.searchQuery.value"
      :card-scale-style="cardScaleStyle"
      :current-card-back-url="currentCardBackUrl"
      :empty-message="deckSelection.emptyMessage.value"
      :filtered-suggestions="deckSelection.filteredSuggestions.value"
      :has-ongoing-playtest="deckSelection.hasOngoingPlaytest.value"
      :open-stack-label="deckSelection.openStackLabel.value"
      :open-stack-zone="deckSelection.openStackZone.value"
      :owned-suggestions="deckSelection.ownedSuggestions.value"
      :public-suggestions="deckSelection.publicSuggestions.value"
      :selected-playtest="deckSelection.selectedPlaytest.value"
      :selected-suggestion="deckSelection.selectedSuggestion.value"
      :selected-suggestion-key="deckSelection.selectedSuggestionKey.value"
      :selector-hand-instances="deckSelection.selectorHandInstances.value"
      :selector-loading="deckSelection.selectorLoading.value"
      :selector-stack-zones="deckSelection.selectorStackZones.value"
      :stack-overlay-instances="deckSelection.stackOverlayInstances.value"
      :stack-popover-bottom-offset-px="deckSelection.stackPopoverBottomOffsetPx.value"
      :visible-suggestion-count="deckSelection.visibleSuggestionCount.value"
      @wheel-scale="handleTableWheel"
      @select-suggestion="deckSelection.selectSuggestion"
      @continue-selected="continueSelectedDeck"
      @start-new-selected="startNewSelectedDeck"
      @open-stack="deckSelection.openPreviewStack"
      @close-stack="deckSelection.closePreviewStack"
      @resize="deckSelection.setLowerBarSize"
    />

    <PlaytestTableSurface
      v-else
      class="playtester-table"
      :style="cardScaleStyle"
      :data-playtest-hover-actions="hoverActions.length"
      :data-playtest-selected-count="selectedBoardInstanceIds.length"
      @wheel="handleTableWheel"
    >
      <div
        v-if="staleDraft"
        class="playtester-stale theme-card-frame"
      >
        <div class="min-w-0">
          <p class="theme-section-title text-sm font-semibold">
            Saved playtest is from an older deck version.
          </p>
          <p class="theme-section-muted mt-1 text-sm">
            Resume the saved board or restart from the current deck list.
          </p>
        </div>
        <div class="flex shrink-0 flex-wrap gap-2">
          <button
            class="btn-secondary"
            type="button"
            @click="resumeStaleDraft"
          >
            Resume Draft
          </button>
          <button
            class="btn-primary"
            type="button"
            @click="restartPlaytest"
          >
            Restart
          </button>
        </div>
      </div>

      <PlaytestOpeningSetup
        v-else-if="playtest?.phase === 'opening'"
        :opening-step="playtest.openingSetup.step"
        :hand-instances="handInstances"
        :library-instances="libraryInstances"
        :mana-instances="openingManaInstances"
        :setup-instances="openingSetupInstances"
        :staged-play-instances="openingStagedPlayInstances"
        :selected-mana-ids="playtest.openingSetup.selectedManaInstanceIds"
        :handled-setup-card-ids="playtest.openingSetup.handledSetupCardIds"
        :hand-size="playtest.handSize"
        :mulligan-count="playtest.openingSetup.mulliganCount"
        :dragging-instance-ids="activeDraggedInstanceIds"
        @continue-mana="continueOpeningMana"
        @continue-setup="continueOpeningSetup"
        @previous-step="previousOpeningStep"
        @select-step="selectOpeningStep"
        @keep="keepOpeningSetup"
        @mulligan="mulliganOpeningSetup"
        @update-hand-size="updateOpeningHandSize"
        @toggle-mana="toggleOpeningMana"
        @toggle-setup-handled="toggleOpeningSetupCardHandled"
        @move-setup-card="moveOpeningSetupCard"
        @pointer-card="startCardPointer"
        @context-card="openCardContextMenu"
        @hover="setHoverTarget"
        @bottom-resize="setLowerBarWidth"
      >
        <template #stacks>
          <div
            class="playtester-piles playtester-opening-piles"
          >
            <PlaytestStack
              v-for="zone in openingStackZones"
              :key="zone.id"
              :zone-id="zone.id"
              :label="zone.label"
              :instances="zone.instances"
              :face="zone.face"
              :card-back-url="currentCardBackUrl"
              :collapsed="zone.collapsed"
              :default-action="zone.defaultAction"
              :interactive="zone.interactive"
              :draggable="zone.draggable"
              :dragging-top="activeDrag?.instanceId === stackTopInstance(zone.id)?.instanceId"
              :shuffling="shufflingStackZone === zone.id"
              @open="openStack"
              @draw="drawFromStack"
              @pointer-top="startStackPointer"
              @context-menu="openStackContextMenu"
              @hover="setHoverTarget"
            />
          </div>
        </template>
      </PlaytestOpeningSetup>

      <PlaytestActiveStage
        v-else
        :active-drag-instance-id="activeDrag?.instanceId ?? null"
        :active-dragged-instance-ids="activeDraggedInstanceIds"
        :board-selection-active="Boolean(boardSelection)"
        :can-reset-setup="Boolean(playtest?.setupSnapshot)"
        :card-scale="cardScale"
        :current-card-back-url="currentCardBackUrl"
        :hand-instances="handInstances"
        :loose-play-instances="loosePlayInstances"
        :play-instances="playInstances"
        :redo-disabled="redoStack.length === 0"
        :selected-board-instance-ids="selectedBoardInstanceIds"
        :selection-box-style="selectionBoxStyle"
        :shuffling-stack-zone="shufflingStackZone"
        :stack-zones="stackZones"
        :undo-disabled="undoStack.length === 0"
        :visual-piles="visualPiles"
        @board-ref="boardRef = $event"
        @undo="undoPlaytestState"
        @redo="redoPlaytestState"
        @release-pointer-focus="releasePointerFocus"
        @update-card-scale="setCardScaleFromInput"
        @next-turn="nextTurn"
        @reset-setup="resetSetup"
        @restart="restartConfirmOpen = true"
        @start-board-selection="startBoardSelection"
        @remember-board-pointer="rememberBoardPointer"
        @activate-card="activateCard"
        @pointer-card="startCardPointer"
        @context-card="openCardContextMenu"
        @hover="setHoverTarget"
        @open-stack="openStack"
        @draw-stack="drawFromStack"
        @pointer-stack="startStackPointer"
        @context-stack="openStackContextMenu"
        @resize="setLowerBarWidth"
      />

      <PlaytestStackPopover
        :open="!staleDraft && Boolean(openStackZone)"
        :title="openStackLabel"
        :instances="stackOverlayInstances"
        :drop-zone-id="openStackZone"
        :dragging-instance-ids="activeDraggedInstanceIds"
        :card-back-url="currentCardBackUrl"
        :card-interactive="true"
        :bottom-offset-px="stackPopoverBottomOffsetPx"
        test-id="playtest-stack-overlay"
        @close="closeStack"
        @pointer-card="startCardPointer"
        @context-card="openCardContextMenu"
        @hover="setHoverTarget"
      />
    </PlaytestTableSurface>

    <ConfirmModal
      :open="restartConfirmOpen"
      title="Restart playtest?"
      message="This clears the saved local playtest and rebuilds from the current deck."
      confirm-label="Restart"
      cancel-label="Cancel"
      @cancel="restartConfirmOpen = false"
      @confirm="restartPlaytest"
    />

    <PlaytestDraggedCardOverlay
      v-for="overlay in activeDraggedOverlays"
      :key="overlay.instance.instanceId"
      :drag="overlay.drag"
      :instance="overlay.instance"
      :card-back-url="currentCardBackUrl"
    />

    <PlaytestContextMenu
      v-if="contextMenu"
      :open="true"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :actions="contextMenu.actions"
      @close="closeContextMenu"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useEventListener } from '@vueuse/core';
import { Gamepad2 } from 'lucide-vue-next';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchDeckDetail, fetchMyDeck } from '@/modules/decks/api';
import type { DeckRecord } from '@/modules/decks/types';
import { fetchCurrentCardBack } from '@/modules/playtester/api';
import PlaytestActiveStage, { type PlaytestActiveVisualPile } from '@/modules/playtester/components/PlaytestActiveStage.vue';
import PlaytestContextMenu from '@/modules/playtester/components/PlaytestContextMenu.vue';
import PlaytestDraggedCardOverlay from '@/modules/playtester/components/PlaytestDraggedCard.vue';
import PlaytestOpeningSetup from '@/modules/playtester/components/PlaytestOpeningSetup.vue';
import PlaytestPreSetupStage from '@/modules/playtester/components/PlaytestPreSetupStage.vue';
import PlaytestStack from '@/modules/playtester/components/PlaytestStack.vue';
import PlaytestStackPopover from '@/modules/playtester/components/PlaytestStackPopover.vue';
import PlaytestTableSurface from '@/modules/playtester/components/PlaytestTableSurface.vue';
import { usePlaytestDeckSelection } from '@/modules/playtester/composables/usePlaytestDeckSelection';
import { usePlaytestHistory } from '@/modules/playtester/composables/usePlaytestHistory';
import { usePlaytestHotkeys } from '@/modules/playtester/composables/usePlaytestHotkeys';
import { createLocalPlaytestStorage } from '@/modules/playtester/localPlaytestStorage';
import {
  acceptOpeningSetup,
  addInstanceToVisualPile,
  cloneCardInstanceSnapshots,
  countZone,
  createInitialPlaytestState,
  deleteCardInstances,
  drawOpeningHand,
  drawCards,
  getOpeningManaInstances,
  getOpeningSetupInstances,
  getZoneInstances,
  isStoredDraftStale,
  moveInstanceToZone,
  moveBoardInstancesByDelta,
  mulliganOpeningHand,
  placeInstanceOnBoard,
  removeInstanceFromVisualPile,
  resetToSetup,
  serializePlaytestDraft,
  setOpeningHandSize,
  setOpeningStep,
  stageOpeningSetupCardForPlay,
  shuffleZone,
  STARTING_MANA_REQUIRED,
  startNextTurn,
  untapAllBoardCards,
  toggleCardFace,
  toggleCardsFace,
  toggleOpeningSetupHandled,
  toggleTapped,
  toggleOpeningManaSelection,
} from '@/modules/playtester/playtestState';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestDraggedCard,
  PlaytestEntityAction,
  PlaytestHoverTarget,
  PlaytestOpeningStep,
  PlaytestState,
  PlaytestZoneId,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';
import {
  boardDropPosition,
  resolvePlaytestDropTarget,
  type PlaytestResolvedDropTarget,
} from '@/modules/playtester/utils/dropTargets';
import {
  getPlaytestCardScaleStyle,
  loadPlaytestCardScale,
  normalizePlaytestCardScale,
  PLAYTEST_CARD_SCALE_STEP,
  savePlaytestCardScale,
} from '@/modules/playtester/utils/cardScale';
import {
  getCollapsedStackZoneIds,
  getPlaytestStackFace,
  PLAYTEST_STACK_DEFINITIONS,
  PLAYTEST_STACK_OPENING_BUDGET_RATIO,
  PLAYTEST_STACK_PLAY_BUDGET_RATIO,
} from '@/modules/playtester/utils/stacks';

type PointerDragStart = {
  instanceId: string;
  source: PlaytestCardSource;
  pointerId: number;
  startX: number;
  startY: number;
  pointerOffsetX: number;
  pointerOffsetY: number;
  sourceWidth: number;
  sourceHeight: number;
  groupInstanceIds: string[];
  groupOffsets: Record<string, { pointerOffsetX: number; pointerOffsetY: number }>;
};

type PlaytestContextMenuState = {
  x: number;
  y: number;
  actions: PlaytestEntityAction[];
};

type BoardSelectionDrag = {
  pointerId: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  initialSelectedInstanceIds: string[];
};

type DraggedCardOverlay = {
  drag: PlaytestDraggedCard;
  instance: PlaytestCardInstance;
};

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const storage = createLocalPlaytestStorage();
const deck = ref<DeckRecord | null>(null);
const playtest = ref<PlaytestState | null>(null);
const staleDraft = ref<StoredPlaytestDraft | null>(null);
const activeDeckLoading = ref(false);
const pendingRouteDeck = ref<{ deck: DeckRecord; draft: StoredPlaytestDraft | null } | null>(null);
const pendingDrag = ref<PointerDragStart | null>(null);
const activeDrag = ref<PlaytestDraggedCard | null>(null);
const selectedBoardInstanceIds = ref<string[]>([]);
const boardSelection = ref<BoardSelectionDrag | null>(null);
const contextMenu = ref<PlaytestContextMenuState | null>(null);
const hoverTarget = ref<PlaytestHoverTarget | null>(null);
const suppressClickUntil = ref(0);
const restartConfirmOpen = ref(false);
const saveSuspended = ref(false);
const cardScale = ref(loadPlaytestCardScale());
const currentCardBackUrl = ref<string | null>(null);
const openStackZone = ref<PlaytestZoneId | null>(null);
const copiedCards = ref<PlaytestCardInstance[]>([]);
const lastBoardPointer = ref<{ x: number; y: number } | null>(null);
const shufflingStackZone = ref<PlaytestZoneId | null>(null);
const boardRef = ref<HTMLElement | null>(null);
const lowerBarWidth = ref(0);
const lowerBarHeight = ref(0);
const DRAG_START_THRESHOLD_PX = 2;
const SELECTION_START_THRESHOLD_PX = 4;
const CLICK_SUPPRESSION_MS = 180;
const STACK_SHUFFLE_ANIMATION_MS = 650;
let shuffleAnimationTimer: number | null = null;
let activeDeckLoadRequestId = 0;
const deckSelection = usePlaytestDeckSelection({
  authenticated: computed(() => auth.authenticated),
  cardScale,
  storage,
});

const setLowerBarWidth = (width: number, height = 0): void => {
  lowerBarWidth.value = width;
  lowerBarHeight.value = height;
};

const deckId = computed(() => String(route.params.deckId ?? ''));
const isPreSetupStage = computed(() => deckId.value === '');
const pageTitle = computed(() => {
  if (isPreSetupStage.value) {
    return 'Playtester';
  }
  return deck.value?.name ?? 'Playtester';
});
const pageSubtitle = computed(() => {
  if (isPreSetupStage.value) {
    return 'Choose a deck and run opening hands, setup, and early turns.';
  }
  return deck.value ? `Hero: ${deck.value.hero_card.name}` : 'Loading deck playtest.';
});
const cardScaleStyle = computed(() => getPlaytestCardScaleStyle(cardScale.value));
const stackPopoverBottomOffsetPx = computed(() =>
  lowerBarHeight.value > 0 ? lowerBarHeight.value + 12 : undefined,
);

const zoneInstances = (zoneId: PlaytestZoneId): PlaytestCardInstance[] =>
  playtest.value ? getZoneInstances(playtest.value, zoneId) : [];

const zoneCount = (zoneId: PlaytestZoneId): number =>
  playtest.value ? countZone(playtest.value, zoneId) : 0;

const playInstances = computed(() => zoneInstances('play'));
const visualPiles = computed<PlaytestActiveVisualPile[]>(() => {
  const groups = new Map<string, PlaytestCardInstance[]>();
  for (const instance of playInstances.value) {
    if (!instance.pileGroupId) {
      continue;
    }
    groups.set(instance.pileGroupId, [...(groups.get(instance.pileGroupId) ?? []), instance]);
  }
  return [...groups.entries()]
    .map(([groupId, instances]) => ({
      groupId,
      instances: [...instances].sort(
        (left, right) =>
          (left.pileOrder ?? left.order) - (right.pileOrder ?? right.order)
          || left.instanceId.localeCompare(right.instanceId),
      ),
    }))
    .filter((pile) => pile.instances.length > 1);
});
const piledInstanceIds = computed(() => new Set(visualPiles.value.flatMap((pile) =>
  pile.instances.map((instance) => instance.instanceId),
)));
const loosePlayInstances = computed(() =>
  playInstances.value.filter((instance) => !piledInstanceIds.value.has(instance.instanceId)),
);
const handInstances = computed(() => zoneInstances('hand'));
const libraryInstances = computed(() => zoneInstances('library'));
const openingManaInstances = computed(() => (playtest.value ? getOpeningManaInstances(playtest.value) : []));
const openingSetupInstances = computed(() => (playtest.value ? getOpeningSetupInstances(playtest.value) : []));
const openingStagedPlayInstances = computed(() => {
  if (!playtest.value) {
    return [];
  }
  const stagedIds = new Set(playtest.value.openingSetup.selectedSetupInstanceIds);
  return zoneInstances('other').filter((instance) => stagedIds.has(instance.instanceId));
});

const stackZones = computed(() =>
  PLAYTEST_STACK_DEFINITIONS.map((zone) => ({
    ...zone,
    face: getPlaytestStackFace(playtest.value?.stackFaces, zone.id),
    collapsed: collapsedStackZoneIds.value.has(zone.id),
    instances: zoneInstances(zone.id),
  })),
);
const openingStackZones = computed(() =>
  stackZones.value
    .map((zone) => ({
      ...zone,
      interactive: playtest.value?.openingSetup.step === 'setup'
        && !(playtest.value?.openingSetup.step === 'setup' && zone.id === 'library'),
      draggable: playtest.value?.openingSetup.step === 'setup'
        && !(playtest.value?.openingSetup.step === 'setup' && zone.id === 'library'),
      defaultAction: 'open' as const,
    })),
);

const activeDraggedInstanceIds = computed(() =>
  activeDrag.value?.groupInstanceIds?.length
    ? activeDrag.value.groupInstanceIds
    : activeDrag.value ? [activeDrag.value.instanceId] : [],
);

const activeDraggedOverlays = computed<DraggedCardOverlay[]>(() => {
  if (!activeDrag.value || !playtest.value) {
    return [];
  }
  const drag = activeDrag.value;
  const ids = drag.groupInstanceIds?.length ? drag.groupInstanceIds : [drag.instanceId];
  return ids.flatMap((instanceId) => {
    const instance = playtest.value?.instances.find((entry) => entry.instanceId === instanceId);
    if (!instance) {
      return [];
    }
    const offset = drag.groupOffsets?.[instanceId] ?? {
      pointerOffsetX: drag.pointerOffsetX,
      pointerOffsetY: drag.pointerOffsetY,
    };
    return [{
      instance,
      drag: {
        ...drag,
        instanceId,
        pointerOffsetX: offset.pointerOffsetX,
        pointerOffsetY: offset.pointerOffsetY,
      },
    }];
  });
});

const selectionBoxStyle = computed(() => {
  if (!boardSelection.value) {
    return {};
  }
  const left = Math.min(boardSelection.value.startX, boardSelection.value.currentX);
  const top = Math.min(boardSelection.value.startY, boardSelection.value.currentY);
  const width = Math.abs(boardSelection.value.currentX - boardSelection.value.startX);
  const height = Math.abs(boardSelection.value.currentY - boardSelection.value.startY);
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
  };
});

const collapsedStackZoneIds = computed(() => {
  if (typeof window === 'undefined' || lowerBarWidth.value <= 0) {
    return new Set<PlaytestZoneId>();
  }
  const rootFontSize = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
  const stackBudgetRatio = !isPreSetupStage.value && playtest.value?.phase === 'opening'
    ? PLAYTEST_STACK_OPENING_BUDGET_RATIO
    : PLAYTEST_STACK_PLAY_BUDGET_RATIO;
  return getCollapsedStackZoneIds(lowerBarWidth.value, cardScale.value, rootFontSize, stackBudgetRatio);
});

const openStackLabel = computed(() => PLAYTEST_STACK_DEFINITIONS.find((zone) => zone.id === openStackZone.value)?.label ?? 'Stack');
const stackOverlayInstances = computed(() => {
  if (!openStackZone.value) {
    return [];
  }
  const instances = zoneInstances(openStackZone.value);
  return openStackZone.value === 'library' ? instances : [...instances].reverse();
});

const fetchVisibleDeck = async (targetDeckId: string): Promise<DeckRecord> => {
  if (auth.authenticated) {
    try {
      return await fetchMyDeck(targetDeckId);
    } catch {
      return await fetchDeckDetail(targetDeckId);
    }
  }
  return await fetchDeckDetail(targetDeckId);
};

const continueSelectedDeck = (): void => {
  const preparedDeck = deckSelection.prepareContinueSelectedDeck();
  if (!preparedDeck) {
    return;
  }
  pendingRouteDeck.value = {
    deck: preparedDeck.deck,
    draft: preparedDeck.draft,
  };
  void router.push(preparedDeck.path);
};

const startNewSelectedDeck = (): void => {
  const preparedDeck = deckSelection.prepareNewSelectedDeck();
  if (!preparedDeck) {
    return;
  }
  pendingRouteDeck.value = {
    deck: preparedDeck.deck,
    draft: preparedDeck.draft,
  };
  void router.push(preparedDeck.path);
};

const pruneSelectedBoardCards = (nextState: PlaytestState): void => {
  selectedBoardInstanceIds.value = selectedBoardInstanceIds.value.filter((instanceId) =>
    nextState.instances.some((instance) => instance.instanceId === instanceId && instance.zoneId === 'play'),
  );
};

const clearUndoRedoTransientUi = (): void => {
  pendingDrag.value = null;
  activeDrag.value = null;
  boardSelection.value = null;
  contextMenu.value = null;
  hoverTarget.value = null;
  openStackZone.value = null;
};

const {
  applyState,
  clearHistory,
  redoStack,
  redoPlaytestState,
  replacePlaytestState,
  undoStack,
  undoPlaytestState,
} = usePlaytestHistory({
  playtest,
  clearSelection: () => {
    selectedBoardInstanceIds.value = [];
  },
  clearTransientUi: clearUndoRedoTransientUi,
  pruneState: pruneSelectedBoardCards,
});

const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

const setCardScale = (value: number): void => {
  cardScale.value = normalizePlaytestCardScale(value);
  savePlaytestCardScale(cardScale.value);
};

const setCardScaleFromInput = (event: Event): void => {
  const input = event.target;
  if (!(input instanceof HTMLInputElement)) {
    return;
  }
  setCardScale(input.valueAsNumber);
};

const releasePointerFocus = (event?: PointerEvent): void => {
  const target = event?.currentTarget;
  if (target instanceof HTMLElement) {
    target.blur();
  }
};

const boardRelativePoint = (event: PointerEvent): { x: number; y: number } | null => {
  const board = boardRef.value;
  if (!board) {
    return null;
  }
  const bounds = board.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return null;
  }
  return {
    x: clamp(event.clientX - bounds.left, 0, bounds.width),
    y: clamp(event.clientY - bounds.top, 0, bounds.height),
  };
};

const boardRelativeMousePoint = (event: MouseEvent | WheelEvent): { x: number; y: number } | null => {
  const board = boardRef.value;
  if (!board) {
    return null;
  }
  const bounds = board.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return null;
  }
  if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) {
    return null;
  }
  return {
    x: ((event.clientX - bounds.left) / bounds.width) * 100,
    y: ((event.clientY - bounds.top) / bounds.height) * 100,
  };
};

const selectBoardCardsInRect = (selection: BoardSelectionDrag): void => {
  const distance = Math.hypot(
    selection.currentX - selection.startX,
    selection.currentY - selection.startY,
  );
  if (distance < SELECTION_START_THRESHOLD_PX) {
    selectedBoardInstanceIds.value = [];
    return;
  }
  const board = boardRef.value;
  if (!board) {
    selectedBoardInstanceIds.value = [];
    return;
  }
  const boardBounds = board.getBoundingClientRect();
  const rect = {
    left: boardBounds.left + Math.min(selection.startX, selection.currentX),
    right: boardBounds.left + Math.max(selection.startX, selection.currentX),
    top: boardBounds.top + Math.min(selection.startY, selection.currentY),
    bottom: boardBounds.top + Math.max(selection.startY, selection.currentY),
  };
  const selectedIds = [...board.querySelectorAll<HTMLElement>('[data-instance-id][data-playtest-zone-id="play"]')]
    .filter((element) => {
      const bounds = element.getBoundingClientRect();
      return bounds.left <= rect.right
        && bounds.right >= rect.left
        && bounds.top <= rect.bottom
        && bounds.bottom >= rect.top;
    })
    .map((element) => element.dataset.instanceId)
    .filter((instanceId): instanceId is string => typeof instanceId === 'string');
  selectedBoardInstanceIds.value = [...new Set(selectedIds)];
};

const nextBoardPosition = (): { x: number; y: number } => {
  const index = playInstances.value.length;
  return {
    x: 16 + (index % 5) * 16,
    y: 22 + Math.floor(index / 5) * 24,
  };
};

const activateCard = (instanceId: string): void => {
  if (Date.now() < suppressClickUntil.value) {
    return;
  }
  if (!playtest.value) {
    return;
  }
  const instance = playtest.value.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance) {
    return;
  }
  if (playtest.value.phase === 'opening') {
    return;
  }
  if (instance.zoneId === 'library') {
    applyState(drawCards(playtest.value, 1));
    return;
  }
  if (instance.zoneId === 'hand') {
    const position = nextBoardPosition();
    applyState(placeInstanceOnBoard(playtest.value, instanceId, position.x, position.y));
    return;
  }
  if (instance.zoneId === 'play') {
    applyState(toggleTapped(playtest.value, instanceId));
  }
};

const openStack = (zoneId: PlaytestZoneId): void => {
  if (Date.now() < suppressClickUntil.value) {
    return;
  }
  if (playtest.value?.phase === 'opening' && playtest.value.openingSetup.step !== 'setup') {
    return;
  }
  openStackZone.value = openStackZone.value === zoneId ? null : zoneId;
};

const closeStack = (): void => {
  openStackZone.value = null;
};

const stackTopInstance = (zoneId: PlaytestZoneId): PlaytestCardInstance | null => {
  const instances = zoneInstances(zoneId);
  return zoneId === 'library' ? instances[0] ?? null : instances[instances.length - 1] ?? null;
};

const startPointerDrag = (
  instanceId: string,
  source: PlaytestCardSource,
  event: PointerEvent,
): void => {
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  const bounds = target.getBoundingClientRect();
  const sourceBounds = source.type === 'stack'
    ? target.querySelector<HTMLElement>('.playtest-stack-card')?.getBoundingClientRect() ?? bounds
    : bounds;
  const selectedPlayIds = selectedBoardInstanceIds.value.filter((selectedId) =>
    playtest.value?.instances.some((instance) =>
      instance.instanceId === selectedId && instance.zoneId === 'play',
    ) === true,
  );
  const isSelectedBoardCard = source.type === 'card'
    && source.zoneId === 'play'
    && selectedPlayIds.includes(instanceId)
    && selectedPlayIds.length > 1;
  const groupInstanceIds = isSelectedBoardCard ? selectedPlayIds : [];
  const groupOffsets = Object.fromEntries(groupInstanceIds.flatMap((selectedId) => {
    const element = boardRef.value?.querySelector<HTMLElement>(`[data-instance-id="${selectedId}"]`);
    if (!element) {
      return [];
    }
    const elementBounds = element.getBoundingClientRect();
    return [[selectedId, {
      pointerOffsetX: event.clientX - elementBounds.left,
      pointerOffsetY: event.clientY - elementBounds.top,
    }]];
  }));
  pendingDrag.value = {
    instanceId,
    source,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    pointerOffsetX: event.clientX - sourceBounds.left,
    pointerOffsetY: event.clientY - sourceBounds.top,
    sourceWidth: sourceBounds.width,
    sourceHeight: sourceBounds.height,
    groupInstanceIds,
    groupOffsets,
  };
  if (!isSelectedBoardCard) {
    selectedBoardInstanceIds.value = [];
  }
  contextMenu.value = null;
  target.setPointerCapture?.(event.pointerId);
  event.preventDefault();
};

const startCardPointer = (instanceId: string, source: PlaytestCardSource, event: PointerEvent): void => {
  startPointerDrag(instanceId, source, event);
};

const startStackPointer = (zoneId: PlaytestZoneId, instanceId: string, event: PointerEvent): void => {
  startPointerDrag(instanceId, { type: 'stack', zoneId }, event);
};

const moveCardToZone = (instanceId: string, zoneId: PlaytestZoneId): void => {
  if (!playtest.value) {
    return;
  }
  if (zoneId === 'play') {
    const position = nextBoardPosition();
    applyState(placeInstanceOnBoard(playtest.value, instanceId, position.x, position.y));
    return;
  }
  applyState(moveInstanceToZone(playtest.value, instanceId, zoneId));
};

const moveCardsToZone = (
  state: PlaytestState,
  instanceIds: string[],
  zoneId: PlaytestZoneId,
  insertionIndex?: number,
): PlaytestState =>
  instanceIds.reduce(
    (nextState, instanceId, index) => moveInstanceToZone(
      nextState,
      instanceId,
      zoneId,
      insertionIndex === undefined ? undefined : insertionIndex + index,
    ),
    state,
  );

const targetIndexAfterRemovingDraggedCard = (
  sourceZoneId: PlaytestZoneId,
  targetZoneId: PlaytestZoneId,
  sourceIndex: number,
  targetIndex: number,
): number => {
  if (sourceZoneId !== targetZoneId || sourceIndex < 0 || targetIndex < 0) {
    return targetIndex;
  }
  return sourceIndex < targetIndex ? targetIndex - 1 : targetIndex;
};

const completeOpeningDraggedCardDrop = (
  drag: PlaytestDraggedCard,
  dropTarget: PlaytestResolvedDropTarget | null,
): void => {
  if (!playtest.value || !dropTarget) {
    return;
  }
  const draggedInstance = playtest.value.instances.find((instance) => instance.instanceId === drag.instanceId);
  if (!draggedInstance || !isOpeningTransferSource(playtest.value, draggedInstance)) {
    return;
  }
  if (dropTarget.type === 'zone') {
    if (!canMoveOpeningTransferToZone(playtest.value, draggedInstance, dropTarget.zoneId) || drag.source.zoneId === dropTarget.zoneId) {
      return;
    }
    applyState(moveOpeningTransferCard(playtest.value, drag.instanceId, dropTarget.zoneId));
    return;
  }

  const target = playtest.value.instances.find((instance) => instance.instanceId === dropTarget.instanceId);
  if (!target || !canMoveOpeningTransferToZone(playtest.value, draggedInstance, target.zoneId)) {
    return;
  }
  const targetZoneInstances = getZoneInstances(playtest.value, target.zoneId);
  const sourceIndex = target.zoneId === drag.source.zoneId
    ? targetZoneInstances.findIndex((instance) => instance.instanceId === drag.instanceId)
    : -1;
  const targetIndex = targetZoneInstances.findIndex((instance) => instance.instanceId === target.instanceId);
  applyState(moveOpeningTransferCard(
    playtest.value,
    drag.instanceId,
    target.zoneId,
    targetIndexAfterRemovingDraggedCard(drag.source.zoneId, target.zoneId, sourceIndex, targetIndex),
  ));
};

const completeDraggedGroupDrop = (drag: PlaytestDraggedCard, pending: PointerDragStart): void => {
  if (!playtest.value || !drag.groupInstanceIds?.length) {
    return;
  }
  const dropTarget = resolvePlaytestDropTarget(drag.pointerX, drag.pointerY, drag.instanceId);
  if (isOpeningPhase()) {
    return;
  }
  if (dropTarget?.type === 'zone' && dropTarget.zoneId !== 'board') {
    applyState(moveCardsToZone(playtest.value, drag.groupInstanceIds, dropTarget.zoneId));
    return;
  }
  if (dropTarget?.type === 'card') {
    const target = playtest.value.instances.find((instance) => instance.instanceId === dropTarget.instanceId);
    if (target && target.zoneId !== 'play') {
      const targetIndex = getZoneInstances(playtest.value, target.zoneId).findIndex(
        (instance) => instance.instanceId === target.instanceId,
      );
      applyState(moveCardsToZone(playtest.value, drag.groupInstanceIds, target.zoneId, targetIndex));
      return;
    }
  }
  const board = boardRef.value;
  if (!board) {
    return;
  }
  const bounds = board.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return;
  }
  if (
    drag.pointerX < bounds.left
    || drag.pointerX > bounds.right
    || drag.pointerY < bounds.top
    || drag.pointerY > bounds.bottom
  ) {
    return;
  }
  const deltaX = ((drag.pointerX - pending.startX) / bounds.width) * 100;
  const deltaY = ((drag.pointerY - pending.startY) / bounds.height) * 100;
  applyState(moveBoardInstancesByDelta(playtest.value, drag.groupInstanceIds, deltaX, deltaY));
};

const completeDraggedCardDrop = (drag: PlaytestDraggedCard): void => {
  if (!playtest.value) {
    return;
  }
  const dropTarget = resolvePlaytestDropTarget(drag.pointerX, drag.pointerY, drag.instanceId);
  if (isOpeningPhase()) {
    completeOpeningDraggedCardDrop(drag, dropTarget);
    return;
  }
  if (!dropTarget) {
    const position = boardDropPosition(boardRef.value, drag);
    if (position) {
      applyState(removeInstanceFromVisualPile(placeInstanceOnBoard(playtest.value, drag.instanceId, position.x, position.y), drag.instanceId));
    }
    return;
  }
  if (dropTarget.type === 'card') {
    const target = playtest.value.instances.find((instance) => instance.instanceId === dropTarget.instanceId);
    if (!target || target.instanceId === drag.instanceId) {
      return;
    }
    if (drag.ctrlKey && target.zoneId === 'play') {
      applyState(addInstanceToVisualPile(playtest.value, drag.instanceId, target.instanceId));
      return;
    }
    if (target.zoneId === 'play') {
      const position = boardDropPosition(boardRef.value, drag) ?? nextBoardPosition();
      applyState(placeInstanceOnBoard(playtest.value, drag.instanceId, position.x, position.y));
      return;
    }
    const targetZoneInstances = getZoneInstances(playtest.value, target.zoneId);
    const sourceIndex = target.zoneId === drag.source.zoneId
      ? targetZoneInstances.findIndex((instance) => instance.instanceId === drag.instanceId)
      : -1;
    const targetIndex = targetZoneInstances.findIndex(
      (instance) => instance.instanceId === target.instanceId,
    );
    applyState(moveInstanceToZone(
      playtest.value,
      drag.instanceId,
      target.zoneId,
      targetIndexAfterRemovingDraggedCard(drag.source.zoneId, target.zoneId, sourceIndex, targetIndex),
    ));
    return;
  }

  if (dropTarget.zoneId === 'board') {
    const position = boardDropPosition(boardRef.value, drag) ?? nextBoardPosition();
    applyState(removeInstanceFromVisualPile(placeInstanceOnBoard(playtest.value, drag.instanceId, position.x, position.y), drag.instanceId));
    return;
  }
  if (drag.source.zoneId === dropTarget.zoneId) {
    return;
  }
  applyState(moveInstanceToZone(playtest.value, drag.instanceId, dropTarget.zoneId));
};

const setHoverTarget = (target: PlaytestHoverTarget | null): void => {
  hoverTarget.value = target;
};

const startBoardSelection = (event: PointerEvent): void => {
  if (event.button !== 0) {
    return;
  }
  const target = event.target;
  if (target instanceof HTMLElement && target.closest('[data-instance-id]')) {
    return;
  }
  const point = boardRelativePoint(event);
  if (!point || !boardRef.value) {
    return;
  }
  boardSelection.value = {
    pointerId: event.pointerId,
    startX: point.x,
    startY: point.y,
    currentX: point.x,
    currentY: point.y,
    initialSelectedInstanceIds: [...selectedBoardInstanceIds.value],
  };
  pendingDrag.value = null;
  activeDrag.value = null;
  contextMenu.value = null;
  boardRef.value.setPointerCapture?.(event.pointerId);
  event.preventDefault();
};

const endActiveDrag = (): void => {
  activeDrag.value = null;
  pendingDrag.value = null;
};

const updatePointerDrag = (event: PointerEvent): void => {
  if (boardSelection.value?.pointerId === event.pointerId) {
    const point = boardRelativePoint(event);
    if (!point) {
      return;
    }
    boardSelection.value = {
      ...boardSelection.value,
      currentX: point.x,
      currentY: point.y,
    };
    selectBoardCardsInRect(boardSelection.value);
    event.preventDefault();
    return;
  }
  const pending = pendingDrag.value;
  if (!pending || pending.pointerId !== event.pointerId) {
    return;
  }
  const distance = Math.hypot(event.clientX - pending.startX, event.clientY - pending.startY);
  if (!activeDrag.value && distance >= DRAG_START_THRESHOLD_PX) {
    activeDrag.value = {
      instanceId: pending.instanceId,
      groupInstanceIds: pending.groupInstanceIds,
      groupOffsets: pending.groupOffsets,
      source: pending.source,
      pointerId: pending.pointerId,
      pointerOffsetX: pending.pointerOffsetX,
      pointerOffsetY: pending.pointerOffsetY,
      sourceWidth: pending.sourceWidth,
      sourceHeight: pending.sourceHeight,
      pointerX: event.clientX,
      pointerY: event.clientY,
      ctrlKey: event.ctrlKey,
      candidate: resolvePlaytestDropTarget(event.clientX, event.clientY, pending.instanceId),
    };
    event.preventDefault();
    return;
  }
  if (activeDrag.value) {
    activeDrag.value = {
      ...activeDrag.value,
      pointerX: event.clientX,
      pointerY: event.clientY,
      ctrlKey: event.ctrlKey,
      candidate: resolvePlaytestDropTarget(event.clientX, event.clientY, activeDrag.value.instanceId),
    };
    event.preventDefault();
  }
};

const finishPointerDrag = (event: PointerEvent): void => {
  if (boardSelection.value?.pointerId === event.pointerId) {
    const point = boardRelativePoint(event);
    const completedSelection = point
      ? {
          ...boardSelection.value,
          currentX: point.x,
          currentY: point.y,
        }
      : boardSelection.value;
    selectBoardCardsInRect(completedSelection);
    boardSelection.value = null;
    event.preventDefault();
    return;
  }
  const pending = pendingDrag.value;
  if (!pending || pending.pointerId !== event.pointerId) {
    return;
  }
  if (activeDrag.value) {
    const completedDrag = {
      ...activeDrag.value,
      pointerX: event.clientX,
      pointerY: event.clientY,
      ctrlKey: event.ctrlKey,
      candidate: resolvePlaytestDropTarget(event.clientX, event.clientY, activeDrag.value.instanceId),
    };
    if (completedDrag.groupInstanceIds?.length) {
      completeDraggedGroupDrop(completedDrag, pending);
    } else {
      completeDraggedCardDrop(completedDrag);
    }
    suppressClickUntil.value = Date.now() + CLICK_SUPPRESSION_MS;
    event.preventDefault();
  }
  endActiveDrag();
};

useEventListener(window, 'pointermove', updatePointerDrag);
useEventListener(window, 'pointerup', finishPointerDrag);

const abortPointerDrag = (event: PointerEvent): void => {
  if (boardSelection.value?.pointerId === event.pointerId) {
    selectedBoardInstanceIds.value = boardSelection.value.initialSelectedInstanceIds;
    boardSelection.value = null;
    event.preventDefault();
    return;
  }
  const activePointerId = activeDrag.value?.pointerId ?? pendingDrag.value?.pointerId;
  if (activePointerId !== event.pointerId) {
    return;
  }
  endActiveDrag();
  event.preventDefault();
};

useEventListener(window, 'pointercancel', abortPointerDrag);

const isPlayHotkeyEnabled = (): boolean =>
  playtest.value?.phase === 'play'
  && staleDraft.value === null
  && !activeDrag.value
  && !pendingDrag.value
  && !boardSelection.value;

const isScaleWheelEnabled = (): boolean =>
  (isPreSetupStage.value || (playtest.value !== null && staleDraft.value === null))
  && !activeDrag.value
  && !pendingDrag.value
  && !boardSelection.value;

const rememberBoardPointer = (event: MouseEvent): void => {
  const point = boardRelativeMousePoint(event);
  if (point) {
    lastBoardPointer.value = point;
  }
};

const handleTableWheel = (event: WheelEvent): void => {
  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || !isScaleWheelEnabled()) {
    return;
  }
  setCardScale(cardScale.value + (event.deltaY < 0 ? PLAYTEST_CARD_SCALE_STEP : -PLAYTEST_CARD_SCALE_STEP));
  event.preventDefault();
};

const hoveredCard = (): PlaytestCardInstance | null => {
  const target = hoverTarget.value;
  if (target?.type !== 'card') {
    return null;
  }
  return playtest.value?.instances.find((instance) => instance.instanceId === target.instanceId) ?? null;
};

const focusedCard = (): PlaytestCardInstance | null => {
  const focusedElement = document.activeElement;
  if (!(focusedElement instanceof HTMLElement) || !focusedElement.closest('.playtester-page')) {
    return null;
  }

  const instanceId = focusedElement.closest<HTMLElement>('[data-instance-id]')?.dataset.instanceId;
  if (!instanceId) {
    return null;
  }

  return playtest.value?.instances.find((instance) => instance.instanceId === instanceId) ?? null;
};

const selectedBoardIds = (): string[] =>
  selectedBoardInstanceIds.value.filter((instanceId) =>
    playtest.value?.instances.some((instance) => instance.instanceId === instanceId && instance.zoneId === 'play') === true,
  );

const hotkeyCardIds = (options: { boardOnly: boolean }): string[] => {
  const hovered = hoveredCard();
  if (hovered && (!options.boardOnly || hovered.zoneId === 'play')) {
    return [hovered.instanceId];
  }
  const focused = focusedCard();
  if (focused && (!options.boardOnly || focused.zoneId === 'play')) {
    return [focused.instanceId];
  }
  return selectedBoardIds();
};

const toggleCardFaceAction = (instanceId: string): void => {
  if (!playtest.value) {
    return;
  }
  applyState(toggleCardFace(playtest.value, instanceId));
};

const toggleTappedCards = (instanceIds: string[]): void => {
  if (!playtest.value || instanceIds.length === 0) {
    return;
  }
  applyState(instanceIds.reduce((nextState, instanceId) => toggleTapped(nextState, instanceId), playtest.value));
};

const deletableCardIds = (instanceIds: string[]): string[] => {
  if (!playtest.value) {
    return [];
  }
  const ids = new Set(instanceIds);
  return playtest.value.instances
    .filter((instance) => ids.has(instance.instanceId) && instance.zoneId !== 'hero')
    .map((instance) => instance.instanceId);
};

const deleteCards = (instanceIds: string[]): boolean => {
  if (!playtest.value) {
    return false;
  }
  const ids = deletableCardIds(instanceIds);
  if (ids.length === 0) {
    return false;
  }
  applyState(deleteCardInstances(playtest.value, ids));
  return true;
};

const copyCards = (instanceIds: string[]): boolean => {
  if (!playtest.value || instanceIds.length === 0) {
    return false;
  }
  copiedCards.value = instanceIds.flatMap((instanceId) => {
    const instance = playtest.value?.instances.find((entry) => entry.instanceId === instanceId);
    return instance ? [{ ...instance }] : [];
  });
  return copiedCards.value.length > 0;
};

const copyCurrentCards = (): boolean => {
  if (!playtest.value || !isPlayHotkeyEnabled()) {
    return false;
  }
  const ids = selectedBoardIds();
  const hovered = hoveredCard();
  const copyIds = ids.length > 0 ? ids : hovered ? [hovered.instanceId] : [];
  return copyCards(copyIds);
};

const pasteCopiedCards = (): boolean => {
  if (!playtest.value || !isPlayHotkeyEnabled() || copiedCards.value.length === 0) {
    return false;
  }
  const anchor = lastBoardPointer.value ?? { x: 50, y: 50 };
  applyState(cloneCardInstanceSnapshots(playtest.value, copiedCards.value, {
    type: 'board',
    anchorX: anchor.x,
    anchorY: anchor.y,
  }));
  return true;
};

const shuffleLibrary = (): boolean => {
  if (!playtest.value || !canShuffleLibrary(playtest.value)) {
    return false;
  }
  applyState(shuffleZone(playtest.value, 'library'));
  shufflingStackZone.value = 'library';
  if (shuffleAnimationTimer) {
    window.clearTimeout(shuffleAnimationTimer);
  }
  shuffleAnimationTimer = window.setTimeout(() => {
    shufflingStackZone.value = null;
    shuffleAnimationTimer = null;
  }, STACK_SHUFFLE_ANIMATION_MS);
  if (openStackZone.value === 'library') {
    closeStack();
  }
  return true;
};

const handlePlaytesterHotkey = (event: KeyboardEvent): boolean => {
  if (!isPlayHotkeyEnabled()) {
    return false;
  }

  const modifierPressed = (event.ctrlKey || event.metaKey) && !event.altKey;
  const normalizedModifiedKey = event.key.toLowerCase();
  const undoPressed = modifierPressed && !event.shiftKey && normalizedModifiedKey === 'z';
  if (undoPressed && undoPlaytestState()) {
    return true;
  }
  const redoPressed = modifierPressed
    && (
      (event.shiftKey && normalizedModifiedKey === 'z')
      || (!event.shiftKey && normalizedModifiedKey === 'y')
    );
  if (redoPressed && redoPlaytestState()) {
    return true;
  }

  const copyPressed = (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'c';
  if (copyPressed && copyCurrentCards()) {
    return true;
  }

  const pastePressed = (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'v';
  if (pastePressed && pasteCopiedCards()) {
    return true;
  }

  const deletePressed =
    !event.ctrlKey
    && !event.metaKey
    && !event.altKey
    && !event.shiftKey
    && (event.key === 'Delete' || event.key === 'Backspace');
  if (deletePressed && deleteCards(hotkeyCardIds({ boardOnly: false }))) {
    return true;
  }

  if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || event.key.length !== 1) {
    return false;
  }

  const normalizedKey = event.key.toLowerCase();
  if (normalizedKey === 'n') {
    return nextTurn();
  }
  if (normalizedKey === 'u') {
    return untapAllCards();
  }
  if (normalizedKey === 'd') {
    return drawOne();
  }
  if (normalizedKey === 't') {
    const ids = hotkeyCardIds({ boardOnly: true });
    if (ids.length > 0) {
      toggleTappedCards(ids);
      return true;
    }
    return false;
  }
  if (normalizedKey === 'f') {
    const ids = hotkeyCardIds({ boardOnly: false });
    if (ids.length > 0 && playtest.value) {
      applyState(toggleCardsFace(playtest.value, ids));
      return true;
    }
    return false;
  }
  if (normalizedKey === 'r') {
    return shuffleLibrary();
  }
  return false;
};

usePlaytestHotkeys({
  enabled: computed(() => !isPreSetupStage.value),
  handleHotkey: handlePlaytesterHotkey,
});

onBeforeUnmount(() => {
  if (shuffleAnimationTimer) {
    window.clearTimeout(shuffleAnimationTimer);
  }
});

const updateOpeningHandSize = (handSize: number): void => {
  if (!playtest.value) {
    return;
  }
  applyState(setOpeningHandSize(playtest.value, handSize), { recordHistory: false });
};

const toggleOpeningMana = (instanceId: string, selected: boolean): void => {
  if (!playtest.value) {
    return;
  }
  applyState(toggleOpeningManaSelection(playtest.value, instanceId, selected), { recordHistory: false });
};

const toggleOpeningSetupCardHandled = (cardId: string, handled: boolean): void => {
  if (!playtest.value) {
    return;
  }
  applyState(toggleOpeningSetupHandled(playtest.value, cardId, handled), { recordHistory: false });
};

const continueOpeningMana = (): void => {
  if (!playtest.value || playtest.value.openingSetup.selectedManaInstanceIds.length !== STARTING_MANA_REQUIRED) {
    return;
  }
  closeStack();
  applyState(setOpeningStep(playtest.value, 'setup'), { recordHistory: false });
};

const continueOpeningSetup = (): void => {
  if (!playtest.value) {
    return;
  }
  closeStack();
  applyState(drawOpeningHand(playtest.value), { recordHistory: false });
};

const previousOpeningStep = (): void => {
  if (!playtest.value) {
    return;
  }
  if (playtest.value.openingSetup.step === 'setup') {
    applyState(setOpeningStep(playtest.value, 'mana'), { recordHistory: false });
    return;
  }
  if (playtest.value.openingSetup.step === 'hand') {
    applyState(setOpeningStep(playtest.value, 'setup'), {
      recordHistory: false,
    });
  }
};

const selectOpeningStep = (targetStep: PlaytestOpeningStep): void => {
  if (!playtest.value || playtest.value.phase !== 'opening') {
    return;
  }
  const visibleSteps: PlaytestOpeningStep[] = ['mana', 'setup', 'hand'];
  const currentIndex = visibleSteps.indexOf(playtest.value.openingSetup.step);
  const targetIndex = visibleSteps.indexOf(targetStep);
  if (targetIndex < 0 || currentIndex < 0 || targetIndex >= currentIndex) {
    return;
  }
  closeStack();
  applyState(setOpeningStep(playtest.value, targetStep), { recordHistory: false });
};

const moveOpeningSetupCard = (instanceId: string, zoneId: PlaytestZoneId): void => {
  if (!playtest.value) {
    return;
  }
  if (zoneId === 'play') {
    applyState(stageOpeningSetupCardForPlay(playtest.value, instanceId));
    return;
  }
  applyState(moveOpeningTransferCard(playtest.value, instanceId, zoneId));
};

const mulliganOpeningSetup = (): void => {
  if (!playtest.value || playtest.value.openingSetup.step !== 'hand') {
    return;
  }
  applyState(mulliganOpeningHand(playtest.value), { recordHistory: false });
};

const keepOpeningSetup = (): void => {
  if (!playtest.value || playtest.value.openingSetup.step !== 'hand') {
    return;
  }
  clearHistory();
  applyState(acceptOpeningSetup(playtest.value), { recordHistory: false });
};

const hasTappedBoardCards = (state: PlaytestState): boolean =>
  state.instances.some((instance) => instance.zoneId === 'play' && instance.tapped);

const hasLibraryCards = (state: PlaytestState): boolean =>
  countZone(state, 'library') > 0;

const canShuffleLibrary = (state: PlaytestState): boolean =>
  countZone(state, 'library') > 1;

const drawOne = (): boolean => {
  if (!playtest.value || !hasLibraryCards(playtest.value)) {
    return false;
  }
  applyState(drawCards(playtest.value, 1));
  return true;
};

const untapAllCards = (): boolean => {
  if (!playtest.value || !hasTappedBoardCards(playtest.value)) {
    return false;
  }
  applyState(untapAllBoardCards(playtest.value));
  return true;
};

const nextTurn = (): boolean => {
  if (!playtest.value || (!hasTappedBoardCards(playtest.value) && !hasLibraryCards(playtest.value))) {
    return false;
  }
  applyState(startNextTurn(playtest.value));
  return true;
};

const drawFromStack = (zoneId: PlaytestZoneId): void => {
  if (Date.now() < suppressClickUntil.value) {
    return;
  }
  if (playtest.value?.phase === 'opening' && playtest.value.openingSetup.step === 'hand') {
    return;
  }
  if (zoneId === 'library') {
    drawOne();
  } else {
    openStack(zoneId);
  }
};

const closeContextMenu = (): void => {
  contextMenu.value = null;
};

const isOpeningPhase = (): boolean => playtest.value?.phase === 'opening';

const isOpeningDestinationZone = (zoneId: PlaytestZoneId | 'board'): zoneId is 'library' | 'hand' | 'discard' | 'banish' | 'hero' =>
  zoneId === 'library' || zoneId === 'hand' || zoneId === 'discard' || zoneId === 'banish' || zoneId === 'hero';

const isOpeningStagedPlaySource = (state: PlaytestState, instance: PlaytestCardInstance): boolean =>
  instance.zoneId === 'other' && state.openingSetup.selectedSetupInstanceIds.includes(instance.instanceId);

const isOpeningTransferSource = (state: PlaytestState, instance: PlaytestCardInstance): boolean =>
  instance.zoneId !== 'hero' && (isOpeningDestinationZone(instance.zoneId) || isOpeningStagedPlaySource(state, instance));

const canMoveOpeningTransferToZone = (
  state: PlaytestState,
  instance: PlaytestCardInstance,
  zoneId: PlaytestZoneId | 'board',
): zoneId is 'library' | 'hand' | 'discard' | 'banish' | 'hero' =>
  isOpeningDestinationZone(zoneId)
  && state.openingSetup.step === 'setup';

const moveOpeningTransferCard = (
  state: PlaytestState,
  instanceId: string,
  zoneId: PlaytestZoneId,
  targetIndex?: number,
): PlaytestState => {
  const instance = state.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance || !isOpeningTransferSource(state, instance) || !canMoveOpeningTransferToZone(state, instance, zoneId)) {
    return state;
  }
  const movedState = moveInstanceToZone(state, instanceId, zoneId, targetIndex);
  return {
    ...movedState,
    openingSetup: {
      ...movedState.openingSetup,
      selectedSetupInstanceIds: movedState.openingSetup.selectedSetupInstanceIds.filter((id) => id !== instanceId),
    },
    instances: movedState.instances.map((instance) =>
      instance.instanceId === instanceId
        ? { ...instance, setupOrigin: zoneId !== 'library' }
        : instance,
    ),
  };
};

const openingCardActions = (instanceId: string, instance: PlaytestCardInstance): PlaytestEntityAction[] => {
  if (!playtest.value || playtest.value.openingSetup.step !== 'setup' || !isOpeningTransferSource(playtest.value, instance)) {
    return [];
  }
  const zoneActions: PlaytestEntityAction[] = [
    { id: 'move-hand', label: 'To Hand', disabled: instance.zoneId === 'hand' || !canMoveOpeningTransferToZone(playtest.value, instance, 'hand'), run: () => moveOpeningSetupCard(instanceId, 'hand') },
    { id: 'move-discard', label: 'To Discard', disabled: instance.zoneId === 'discard', run: () => moveOpeningSetupCard(instanceId, 'discard') },
    { id: 'move-banish', label: 'To Banish', disabled: instance.zoneId === 'banish', run: () => moveOpeningSetupCard(instanceId, 'banish') },
    { id: 'move-library', label: 'To Library', disabled: instance.zoneId === 'library', run: () => moveOpeningSetupCard(instanceId, 'library') },
    { id: 'move-hero', label: 'To Hero', disabled: instance.zoneId === 'hero', run: () => moveOpeningSetupCard(instanceId, 'hero') },
  ].filter((action) => !action.disabled);

  if (zoneActions[0]) {
    zoneActions[0] = { ...zoneActions[0], dividerBefore: true };
  }
  return zoneActions;
};

const cardActions = (instanceId: string): PlaytestEntityAction[] => {
  const instance = playtest.value?.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance) {
    return [];
  }
  if (isOpeningPhase()) {
    return openingCardActions(instanceId, instance);
  }
  const zoneActions: PlaytestEntityAction[] = [
    { id: 'move-hand', label: 'To Hand', dividerBefore: true, disabled: instance.zoneId === 'hand', run: () => moveCardToZone(instanceId, 'hand') },
    { id: 'move-play', label: 'To Board', disabled: instance.zoneId === 'play', run: () => moveCardToZone(instanceId, 'play') },
    { id: 'move-discard', label: 'To Discard', disabled: instance.zoneId === 'discard', run: () => moveCardToZone(instanceId, 'discard') },
    { id: 'move-banish', label: 'To Banish', disabled: instance.zoneId === 'banish', run: () => moveCardToZone(instanceId, 'banish') },
    { id: 'move-library', label: 'To Library', disabled: instance.zoneId === 'library', run: () => moveCardToZone(instanceId, 'library') },
  ];
  return [
    { id: 'copy-card', label: 'Copy', hotkey: 'Ctrl+C', run: () => copyCards([instanceId]) },
    { id: 'flip-card', label: instance.face === 'front' ? 'Flip Down' : 'Flip Up', hotkey: 'F', run: () => toggleCardFaceAction(instanceId) },
    ...(instance.zoneId === 'play'
      ? [{ id: 'tap', label: instance.tapped ? 'Untap' : 'Tap', hotkey: 'T', run: () => applyState(toggleTapped(playtest.value as PlaytestState, instanceId)) }]
      : []),
    ...(instance.pileGroupId
      ? [{ id: 'remove-pile', label: 'Unpile', run: () => playtest.value && applyState(removeInstanceFromVisualPile(playtest.value, instanceId)) }]
      : []),
    {
      id: 'delete-card',
      label: 'Delete',
      hotkey: 'Del',
      variant: 'danger',
      disabled: instance.zoneId === 'hero',
      run: () => deleteCards([instanceId]),
    },
    ...zoneActions,
  ];
};

const openingStackActions = (zoneId: PlaytestZoneId, hasCards: boolean): PlaytestEntityAction[] => {
  if (playtest.value?.openingSetup.step !== 'setup') {
    return [];
  }
  const actions: PlaytestEntityAction[] = [
    { id: 'stack-open', label: 'Open', disabled: !hasCards, run: () => openStack(zoneId) },
  ];
  if (!isOpeningDestinationZone(zoneId) || zoneId === 'hero') {
    return actions;
  }
  const topInstance = stackTopInstance(zoneId);
  const zoneActions: PlaytestEntityAction[] = [
    { id: 'top-hand', label: 'Top to Hand', disabled: !topInstance || !playtest.value || zoneId === 'hand' || !canMoveOpeningTransferToZone(playtest.value, topInstance, 'hand'), run: () => moveTopStackCard(zoneId, 'hand') },
    { id: 'top-discard', label: 'Top to Discard', disabled: !hasCards || zoneId === 'discard', run: () => moveTopStackCard(zoneId, 'discard') },
    { id: 'top-banish', label: 'Top to Banish', disabled: !hasCards || zoneId === 'banish', run: () => moveTopStackCard(zoneId, 'banish') },
    { id: 'top-library', label: 'Top to Library', disabled: !hasCards || zoneId === 'library', run: () => moveTopStackCard(zoneId, 'library') },
    { id: 'top-hero', label: 'Top to Hero', disabled: !hasCards, run: () => moveTopStackCard(zoneId, 'hero') },
  ].filter((action) => !action.disabled);

  if (zoneActions[0]) {
    zoneActions[0] = { ...zoneActions[0], dividerBefore: true };
  }
  return [...actions, ...zoneActions];
};

const stackActions = (zoneId: PlaytestZoneId): PlaytestEntityAction[] => {
  const definition = PLAYTEST_STACK_DEFINITIONS.find((zone) => zone.id === zoneId);
  const hasCards = zoneCount(zoneId) > 0;
  if (isOpeningPhase()) {
    return openingStackActions(zoneId, hasCards);
  }
  const defaultActions: PlaytestEntityAction[] =
    definition?.defaultAction === 'draw'
      ? [
          {
            id: 'stack-default',
            label: 'Draw',
            hotkey: 'D',
            disabled: !hasCards,
            run: () => drawFromStack(zoneId),
          },
        ]
      : [];

  return [
    ...defaultActions,
    ...(zoneId === 'library'
      ? [{
          id: 'stack-shuffle',
          label: 'Shuffle',
          hotkey: 'R',
          disabled: !playtest.value || !canShuffleLibrary(playtest.value),
          run: shuffleLibrary,
        }]
      : []),
    { id: 'stack-open', label: 'Open', disabled: !hasCards, run: () => openStack(zoneId) },
    { id: 'top-hand', label: 'Top to Hand', dividerBefore: true, disabled: !hasCards, run: () => moveTopStackCard(zoneId, 'hand') },
    { id: 'top-play', label: 'Top to Board', disabled: !hasCards, run: () => moveTopStackCard(zoneId, 'play') },
    { id: 'top-discard', label: 'Top to Discard', disabled: !hasCards || zoneId === 'discard', run: () => moveTopStackCard(zoneId, 'discard') },
    { id: 'top-banish', label: 'Top to Banish', disabled: !hasCards || zoneId === 'banish', run: () => moveTopStackCard(zoneId, 'banish') },
  ];
};

const hoverActions = computed<PlaytestEntityAction[]>(() => {
  if (!hoverTarget.value) {
    return [];
  }
  return hoverTarget.value.type === 'card'
    ? cardActions(hoverTarget.value.instanceId)
    : stackActions(hoverTarget.value.zoneId);
});

const openCardContextMenu = (instanceId: string, event: MouseEvent): void => {
  contextMenu.value = {
    x: event.clientX,
    y: event.clientY,
    actions: cardActions(instanceId),
  };
};

const openStackContextMenu = (zoneId: PlaytestZoneId, event: MouseEvent): void => {
  contextMenu.value = {
    x: event.clientX,
    y: event.clientY,
    actions: stackActions(zoneId),
  };
};

const moveTopStackCard = (fromZoneId: PlaytestZoneId, toZoneId: PlaytestZoneId): void => {
  if (!playtest.value) {
    return;
  }
  const top = stackTopInstance(fromZoneId);
  if (!top) {
    return;
  }
  if (isOpeningPhase()) {
    if (fromZoneId === 'hero') {
      return;
    }
    applyState(moveOpeningTransferCard(playtest.value, top.instanceId, toZoneId));
    return;
  }
  moveCardToZone(top.instanceId, toZoneId);
};

const resetSetup = (): void => {
  if (playtest.value) {
    applyState(resetToSetup(playtest.value));
  }
};

const restartPlaytest = (): void => {
  if (!deck.value) {
    return;
  }
  saveSuspended.value = false;
  storage.clear(deck.value.id);
  staleDraft.value = null;
  restartConfirmOpen.value = false;
  replacePlaytestState(createInitialPlaytestState(deck.value));
};

const loadCurrentCardBack = async (): Promise<void> => {
  try {
    const response = await fetchCurrentCardBack();
    currentCardBackUrl.value = response.current?.image_url ? toAbsoluteApiUrl(response.current.image_url) : null;
  } catch {
    currentCardBackUrl.value = null;
  }
};

const resumeStaleDraft = (): void => {
  if (!staleDraft.value) {
    return;
  }
  saveSuspended.value = false;
  replacePlaytestState(staleDraft.value.state);
  staleDraft.value = null;
};

watch(
  playtest,
  (state) => {
    if (!state || saveSuspended.value) {
      return;
    }
    storage.save(serializePlaytestDraft(state));
  },
);

const resetTransientPlaytestUi = (): void => {
  pendingDrag.value = null;
  activeDrag.value = null;
  selectedBoardInstanceIds.value = [];
  boardSelection.value = null;
  contextMenu.value = null;
  hoverTarget.value = null;
  openStackZone.value = null;
  restartConfirmOpen.value = false;
};

const applyLoadedDeck = (
  loadedDeck: DeckRecord,
  preferredDraft: StoredPlaytestDraft | null = null,
): void => {
  deck.value = loadedDeck;
  const draft = preferredDraft ?? storage.load(loadedDeck.id);
  if (draft && !isStoredDraftStale(draft, loadedDeck)) {
    replacePlaytestState(draft.state);
    return;
  }
  if (draft) {
    staleDraft.value = draft;
    saveSuspended.value = true;
  }
  replacePlaytestState(createInitialPlaytestState(loadedDeck));
};

const enterPreSetupStage = (): void => {
  activeDeckLoadRequestId += 1;
  activeDeckLoading.value = false;
  deck.value = null;
  replacePlaytestState(null);
  staleDraft.value = null;
  saveSuspended.value = false;
  pendingRouteDeck.value = null;
  resetTransientPlaytestUi();
  if (deckSelection.suggestions.value.length === 0) {
    void deckSelection.loadSuggestions();
  }
};

const loadPlaytestDeck = async (targetDeckId: string): Promise<void> => {
  const requestId = ++activeDeckLoadRequestId;
  activeDeckLoading.value = true;
  deck.value = null;
  replacePlaytestState(null);
  staleDraft.value = null;
  saveSuspended.value = false;
  resetTransientPlaytestUi();
  try {
    const pendingDeck = pendingRouteDeck.value;
    if (pendingDeck?.deck.id === targetDeckId) {
      pendingRouteDeck.value = null;
      applyLoadedDeck(pendingDeck.deck, pendingDeck.draft);
      return;
    }
    const loadedDeck = await fetchVisibleDeck(targetDeckId);
    if (requestId !== activeDeckLoadRequestId) {
      return;
    }
    applyLoadedDeck(loadedDeck);
  } finally {
    if (requestId === activeDeckLoadRequestId) {
      activeDeckLoading.value = false;
    }
  }
};

watch(
  deckId,
  (nextDeckId) => {
    if (!nextDeckId) {
      enterPreSetupStage();
      return;
    }
    void loadPlaytestDeck(nextDeckId);
  },
  { immediate: true },
);

onMounted(() => {
  void loadCurrentCardBack();
});
</script>

<style scoped>
.playtester-page {
  width: 100%;
  min-height: calc(100dvh - var(--app-page-header-height, 0px));
  height: calc(100dvh - var(--app-page-header-height, 0px));
  overflow: hidden;
}

.playtester-loading {
  flex: 1 1 auto;
  min-height: 0;
  border-radius: 0;
  background:
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    var(--color-surface-strong);
  background-size: 1.4rem 1.4rem;
}

.playtester-stale {
  position: relative;
  z-index: 30;
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin: 0.75rem;
  padding: 1rem;
  border-radius: 0.75rem;
}

.playtester-zone-heading,
.playtester-hand-bar,
.playtester-pile-title,
.playtester-pile-count {
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
  user-select: none;
}

.playtester-library-browser {
  position: absolute;
  z-index: 30;
  width: min(17rem, calc(100% - 2rem));
  border: 1px solid var(--playtest-border);
  border-radius: 0.75rem;
  background: var(--playtest-panel);
  box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(14px);
}

.playtester-library-browser {
  bottom: 1rem;
  left: 1rem;
  padding: 0.75rem;
}

.playtester-zone-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.playtester-library-results,
.playtester-pile-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.playtester-library-results {
  max-height: 16rem;
  overflow: auto;
  padding-right: 0.2rem;
}

.playtester-piles {
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 0.75rem;
}

.playtester-opening-piles {
  align-self: stretch;
  overflow: visible;
}

@media (max-width: 900px) {
  .playtester-page-pre-setup {
    height: auto;
    min-height: calc(100dvh - var(--app-page-header-height, 0px));
    overflow: visible;
  }
}

@media (max-width: 767px) {
  .playtester-stale {
    align-items: stretch;
    flex-direction: column;
  }

  .playtester-library-browser {
    position: relative;
    inset: auto;
    width: auto;
    margin: 0.75rem;
  }

  .playtester-piles {
    gap: 0.5rem;
  }

}

</style>
