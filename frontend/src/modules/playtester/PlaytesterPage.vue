<template>
  <section class="playtester-page flex flex-col">
    <AppPageHeader
      :icon="Gamepad2"
      :title="deck?.name ?? 'Playtester'"
      :subtitle="deck ? `Hero: ${deck.hero_card.name}` : 'Loading deck playtest.'"
      back-to="/playtester"
      back-label="Back to Playtester"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <RouterLink
          v-if="deck"
          class="btn-secondary"
          :to="`/decks/${deck.id}`"
        >
          Deck Detail
        </RouterLink>
      </template>
    </AppPageHeader>

    <div
      v-if="loading"
      class="playtester-loading theme-card-frame-muted"
      aria-label="Loading playtester"
    />

    <div
      v-else-if="!deck || !playtest"
      class="theme-empty-state text-sm"
    >
      Deck not found.
    </div>

    <section
      v-else
      class="playtester-table"
      :style="cardScaleStyle"
      :data-playtest-hover-actions="hoverActions.length"
      :data-playtest-selected-count="selectedBoardInstanceIds.length"
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
        v-if="playtest.phase === 'opening'"
        :hand-instances="handInstances"
        :mana-instances="openingManaInstances"
        :setup-instances="openingSetupInstances"
        :selected-mana-ids="playtest.openingSetup.selectedManaInstanceIds"
        :selected-setup-ids="playtest.openingSetup.selectedSetupInstanceIds"
        :hand-size="playtest.handSize"
        @keep="keepOpeningSetup"
        @mulligan="mulliganOpeningSetup"
        @update-hand-size="updateOpeningHandSize"
        @toggle-mana="toggleOpeningMana"
        @toggle-setup="toggleOpeningSetup"
      />

      <template v-else>
        <div class="playtester-topbar">
          <div class="flex flex-wrap items-center gap-2">
            <span
              class="theme-pill theme-pill-success text-xs"
            >
              Play
            </span>
            <span class="theme-pill theme-pill-neutral text-xs">Library {{ zoneCount('library') }}</span>
            <span class="theme-pill theme-pill-neutral text-xs">Hand {{ zoneCount('hand') }}</span>
            <span class="theme-pill theme-pill-neutral text-xs">Board {{ zoneCount('play') }}</span>
          </div>

          <div class="flex flex-wrap items-center justify-end gap-2">
            <button
              class="btn-primary"
              type="button"
              @click="nextTurn"
            >
              Next turn
            </button>
            <button
              class="btn-secondary"
              type="button"
              :disabled="!playtest.setupSnapshot"
              @click="resetSetup"
            >
              Reset to Setup
            </button>
            <button
              class="btn-danger-secondary"
              type="button"
              @click="restartConfirmOpen = true"
            >
              Restart
            </button>
          </div>
        </div>

        <div
          ref="boardRef"
          class="playtester-board"
          data-testid="playtest-board-zone"
          data-playtest-drop-zone="board"
          @pointerdown="startBoardSelection"
        >
          <div class="playtester-board-label">
            <span>Board</span>
            <span>{{ playInstances.length }} cards</span>
          </div>

          <div
            v-if="playInstances.length === 0"
            class="playtester-board-empty"
          >
            Drag cards here or click a card in hand.
          </div>

          <div
            v-for="pile in visualPiles"
            :key="pile.groupId"
            class="playtester-board-pile"
          >
            <PlaytestVisualPile
              :group-id="pile.groupId"
              :instances="pile.instances"
              :dragged-instance-ids="activeDraggedInstanceIds"
              :selected-instance-ids="selectedBoardInstanceIds"
              @activate="activateCard"
              @pointer-card="startCardPointer"
              @context-menu="openCardContextMenu"
              @hover="setHoverTarget"
            />
          </div>

          <div
            v-for="(instance, index) in loosePlayInstances"
            :key="instance.instanceId"
            class="playtester-board-card"
            data-testid="playtest-board-card"
            :style="boardCardStyle(instance, index)"
          >
            <PlaytestCard
              :instance="instance"
              :dragging="isInstanceDragging(instance.instanceId)"
              :selected="selectedBoardInstanceIds.includes(instance.instanceId)"
              @activate="activateCard"
              @pointer-card="startCardPointer"
              @context-menu="openCardContextMenu"
              @hover="setHoverTarget"
            />
          </div>

          <div
            v-if="boardSelection"
            class="playtester-selection-box"
            data-testid="playtest-selection-box"
            :style="selectionBoxStyle"
          />
        </div>

        <div
          ref="lowerBarRef"
          class="playtester-lower"
        >
          <div
            class="playtester-hand"
            data-testid="playtest-hand-zone"
            data-playtest-drop-zone="hand"
          >
            <div class="playtester-hand-bar">
              <span>Cards in hand: {{ handInstances.length }}</span>
              <span class="theme-section-muted">Click a card to put it on the board.</span>
            </div>
            <div class="playtester-hand-fan">
              <div
                v-for="(instance, index) in handInstances"
                :key="instance.instanceId"
                class="playtester-hand-card"
                :style="handCardStyle(index, handInstances.length)"
              >
                <PlaytestCard
                  :instance="instance"
                  :dragging="isInstanceDragging(instance.instanceId)"
                  @activate="activateCard"
                  @pointer-card="startCardPointer"
                  @context-menu="openCardContextMenu"
                  @hover="setHoverTarget"
                />
              </div>
            </div>
          </div>

          <div class="playtester-piles">
            <PlaytestStack
              v-for="zone in stackZones"
              :key="zone.id"
              :zone-id="zone.id"
              :label="zone.label"
              :instances="zone.instances"
              :face="zone.face"
              :card-back-url="currentCardBackUrl"
              :collapsed="zone.collapsed"
              :default-action="zone.defaultAction"
              :dragging-top="activeDrag?.instanceId === stackTopInstance(zone.id)?.instanceId"
              @open="openStack"
              @draw="drawFromStack"
              @pointer-top="startStackPointer"
              @context-menu="openStackContextMenu"
              @hover="setHoverTarget"
            />
          </div>
        </div>

        <div
          v-if="openStackZone"
          class="playtester-stack-popover"
          data-testid="playtest-stack-overlay"
        >
          <section class="playtester-stack-panel">
            <header class="playtester-stack-panel-header">
              <div>
                <h3>{{ openStackLabel }}</h3>
                <p>{{ stackOverlayInstances.length }} cards</p>
              </div>
              <button
                class="btn-secondary"
                type="button"
                @click="closeStack"
              >
                Close
              </button>
            </header>
            <div class="playtester-stack-card-grid app-scrollbar">
              <PlaytestCard
                v-for="instance in stackOverlayInstances"
                :key="instance.instanceId"
                :instance="instance"
                :dragging="isInstanceDragging(instance.instanceId)"
                @activate="noopCardActivate"
                @pointer-card="startCardPointer"
                @context-menu="openCardContextMenu"
                @hover="setHoverTarget"
              />
            </div>
          </section>
        </div>

        <footer class="playtester-footer">
          <div class="flex flex-wrap items-center gap-2">
            <span class="theme-pill theme-pill-neutral text-xs">Discard {{ zoneCount('discard') }}</span>
            <span class="theme-pill theme-pill-neutral text-xs">Banish {{ zoneCount('banish') }}</span>
            <span class="theme-pill theme-pill-neutral text-xs">Hero {{ zoneCount('hero') }}</span>
            <span
              v-if="deck.sideboards.length > 0"
              class="theme-pill theme-pill-neutral text-xs"
            >
              Sideboards {{ deck.sideboards.length }}
            </span>
          </div>

          <label class="theme-section-muted flex items-center gap-2 text-sm font-semibold">
            Card size
            <input
              v-model.number="cardScale"
              class="playtester-scale"
              type="range"
              min="0.75"
              max="1.35"
              step="0.05"
            >
          </label>
        </footer>

        <section
          v-if="deck.sideboards.length > 0"
          class="playtester-sideboards"
        >
          <details>
            <summary>Sideboard reference</summary>
            <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div
                v-for="sideboard in deck.sideboards"
                :key="sideboard.id"
                class="theme-card-frame rounded-lg p-3"
              >
                <div class="flex items-center justify-between gap-3">
                  <p class="theme-section-title text-sm font-semibold">
                    {{ sideboard.name }}
                  </p>
                  <span class="theme-pill theme-pill-neutral text-xs">{{ sideboard.total_cards }}</span>
                </div>
                <div class="mt-2 space-y-1">
                  <p
                    v-for="entry in sideboard.entries"
                    :key="entry.card.id"
                    class="theme-section-muted flex justify-between gap-2 text-xs"
                  >
                    <span class="truncate">{{ entry.card.name }}</span>
                    <span>x{{ entry.quantity }}</span>
                  </p>
                </div>
              </div>
            </div>
          </details>
        </section>
      </template>
    </section>

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
import { computed, onMounted, ref, watch } from 'vue';
import { useEventListener, useResizeObserver } from '@vueuse/core';
import { Gamepad2 } from 'lucide-vue-next';
import { RouterLink, useRoute } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchDeckDetail, fetchMyDeck } from '@/modules/decks/api';
import type { DeckRecord } from '@/modules/decks/types';
import { fetchCurrentCardBack } from '@/modules/playtester/api';
import PlaytestCard from '@/modules/playtester/components/PlaytestCard.vue';
import PlaytestContextMenu from '@/modules/playtester/components/PlaytestContextMenu.vue';
import PlaytestDraggedCardOverlay from '@/modules/playtester/components/PlaytestDraggedCard.vue';
import PlaytestOpeningSetup from '@/modules/playtester/components/PlaytestOpeningSetup.vue';
import PlaytestStack from '@/modules/playtester/components/PlaytestStack.vue';
import PlaytestVisualPile from '@/modules/playtester/components/PlaytestVisualPile.vue';
import { createLocalPlaytestStorage } from '@/modules/playtester/localPlaytestStorage';
import {
  acceptOpeningSetup,
  addInstanceToVisualPile,
  countZone,
  createInitialPlaytestState,
  DEFAULT_PLAYTEST_STACK_FACES,
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
  startNextTurn,
  toggleTapped,
  toggleOpeningManaSelection,
  toggleOpeningSetupSelection,
} from '@/modules/playtester/playtestState';
import type {
  PlaytestCardInstance,
  PlaytestCardSource,
  PlaytestDraggedCard,
  PlaytestEntityAction,
  PlaytestHoverTarget,
  PlaytestStackDefinition,
  PlaytestStackFace,
  PlaytestState,
  PlaytestZoneId,
  StoredPlaytestDraft,
} from '@/modules/playtester/types';

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

type VisualPile = {
  groupId: string;
  instances: PlaytestCardInstance[];
};

type BoardSelectionDrag = {
  pointerId: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
};

type DraggedCardOverlay = {
  drag: PlaytestDraggedCard;
  instance: PlaytestCardInstance;
};

type ResolvedDropTarget = { type: 'card'; instanceId: string } | { type: 'zone'; zoneId: PlaytestZoneId | 'board' };

const route = useRoute();
const auth = useAuthStore();
const storage = createLocalPlaytestStorage();
const deck = ref<DeckRecord | null>(null);
const playtest = ref<PlaytestState | null>(null);
const staleDraft = ref<StoredPlaytestDraft | null>(null);
const loading = ref(true);
const pendingDrag = ref<PointerDragStart | null>(null);
const activeDrag = ref<PlaytestDraggedCard | null>(null);
const selectedBoardInstanceIds = ref<string[]>([]);
const boardSelection = ref<BoardSelectionDrag | null>(null);
const contextMenu = ref<PlaytestContextMenuState | null>(null);
const hoverTarget = ref<PlaytestHoverTarget | null>(null);
const suppressClickUntil = ref(0);
const restartConfirmOpen = ref(false);
const saveSuspended = ref(false);
const cardScale = ref(1);
const currentCardBackUrl = ref<string | null>(null);
const openStackZone = ref<PlaytestZoneId | null>(null);
const boardRef = ref<HTMLElement | null>(null);
const lowerBarRef = ref<HTMLElement | null>(null);
const lowerBarWidth = ref(0);
const DRAG_START_THRESHOLD_PX = 2;
const SELECTION_START_THRESHOLD_PX = 4;
const CLICK_SUPPRESSION_MS = 180;

const deckId = computed(() => String(route.params.deckId ?? ''));
const cardScaleStyle = computed(() => ({
  '--playtest-card-width': `${(9.75 * cardScale.value).toFixed(2)}rem`,
  '--playtest-compact-card-width': `${(6.15 * cardScale.value).toFixed(2)}rem`,
  '--playtest-stack-full-width': `${(11.35 * cardScale.value).toFixed(2)}rem`,
  '--playtest-stack-button-width': `${(3.25 * Math.min(cardScale.value, 1.12)).toFixed(2)}rem`,
}));

const zoneInstances = (zoneId: PlaytestZoneId): PlaytestCardInstance[] =>
  playtest.value ? getZoneInstances(playtest.value, zoneId) : [];

const zoneCount = (zoneId: PlaytestZoneId): number =>
  playtest.value ? countZone(playtest.value, zoneId) : 0;

const playInstances = computed(() => zoneInstances('play'));
const visualPiles = computed<VisualPile[]>(() => {
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
const openingManaInstances = computed(() => (playtest.value ? getOpeningManaInstances(playtest.value) : []));
const openingSetupInstances = computed(() => (playtest.value ? getOpeningSetupInstances(playtest.value) : []));
const stackZoneDefinitions: PlaytestStackDefinition[] = [
  { id: 'library', label: 'Library', defaultAction: 'draw' },
  { id: 'discard', label: 'Discard', defaultAction: 'open' },
  { id: 'banish', label: 'Banish', defaultAction: 'open' },
  { id: 'hero', label: 'Hero', defaultAction: 'open' },
];
const stackCollapseOrder: PlaytestZoneId[] = ['hero', 'banish', 'discard', 'library'];

const stackFace = (zoneId: PlaytestZoneId): PlaytestStackFace =>
  playtest.value?.stackFaces?.[zoneId] ?? DEFAULT_PLAYTEST_STACK_FACES[zoneId] ?? 'front';

const stackZones = computed(() =>
  stackZoneDefinitions.map((zone) => ({
    ...zone,
    face: stackFace(zone.id),
    collapsed: collapsedStackZoneIds.value.has(zone.id),
    instances: zoneInstances(zone.id),
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

const stackLayoutMetrics = computed(() => {
  if (typeof window === 'undefined' || lowerBarWidth.value <= 0) {
    return {
      buttonWidth: 0,
      collapsedCount: 0,
      fullWidth: 0,
      gap: 0,
      stackWidthBudget: Number.POSITIVE_INFINITY,
    };
  }

  const rootFontSize = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
  const fullWidth = 11.35 * cardScale.value * rootFontSize;
  const buttonWidth = 3.25 * Math.min(cardScale.value, 1.12) * rootFontSize;
  const gap = 0.75 * rootFontSize;
  const stackWidthBudget = Math.max((buttonWidth * 4) + (gap * 3), lowerBarWidth.value * 0.52);
  let collapsedCount = 0;

  for (let count = 0; count <= stackCollapseOrder.length; count += 1) {
    const expandedCount = stackCollapseOrder.length - count;
    const requiredWidth = (expandedCount * fullWidth) + (count * buttonWidth) + (gap * 3);
    if (requiredWidth <= stackWidthBudget) {
      collapsedCount = count;
      break;
    }
    collapsedCount = count;
  }

  return {
    buttonWidth,
    collapsedCount,
    fullWidth,
    gap,
    stackWidthBudget,
  };
});

const collapsedStackZoneIds = computed(
  () => new Set<PlaytestZoneId>(stackCollapseOrder.slice(0, stackLayoutMetrics.value.collapsedCount)),
);

const openStackLabel = computed(() => stackZoneDefinitions.find((zone) => zone.id === openStackZone.value)?.label ?? 'Stack');
const stackOverlayInstances = computed(() => {
  if (!openStackZone.value) {
    return [];
  }
  const instances = zoneInstances(openStackZone.value);
  return openStackZone.value === 'library' ? instances : [...instances].reverse();
});

const fetchVisibleDeck = async (): Promise<DeckRecord> => {
  if (auth.authenticated) {
    try {
      return await fetchMyDeck(deckId.value);
    } catch {
      return await fetchDeckDetail(deckId.value);
    }
  }
  return await fetchDeckDetail(deckId.value);
};

const applyState = (nextState: PlaytestState): void => {
  playtest.value = nextState;
  selectedBoardInstanceIds.value = selectedBoardInstanceIds.value.filter((instanceId) =>
    nextState.instances.some((instance) => instance.instanceId === instanceId && instance.zoneId === 'play'),
  );
};

const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

const isInstanceDragging = (instanceId: string): boolean =>
  activeDrag.value?.instanceId === instanceId
  || activeDrag.value?.groupInstanceIds?.includes(instanceId) === true;

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

const noopCardActivate = (): void => undefined;

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

const boardDropPosition = (drag: Pick<PlaytestDraggedCard, 'pointerX' | 'pointerY' | 'pointerOffsetX' | 'pointerOffsetY' | 'sourceWidth' | 'sourceHeight'>): { x: number; y: number } | null => {
  const board = document.querySelector<HTMLElement>('[data-testid="playtest-board-zone"]');
  if (!board) {
    return null;
  }
  const bounds = board.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return null;
  }
  if (drag.pointerX < bounds.left || drag.pointerX > bounds.right || drag.pointerY < bounds.top || drag.pointerY > bounds.bottom) {
    return null;
  }
  const centerX = drag.pointerX - drag.pointerOffsetX + drag.sourceWidth / 2;
  const centerY = drag.pointerY - drag.pointerOffsetY + drag.sourceHeight / 2;
  return {
    x: ((centerX - bounds.left) / bounds.width) * 100,
    y: ((centerY - bounds.top) / bounds.height) * 100,
  };
};

const resolveDropTarget = (
  clientX: number,
  clientY: number,
  draggedInstanceId?: string,
): ResolvedDropTarget | null => {
  const elements = typeof document.elementsFromPoint === 'function'
    ? document.elementsFromPoint(clientX, clientY)
    : typeof document.elementFromPoint === 'function'
      ? [document.elementFromPoint(clientX, clientY)].filter(Boolean)
      : [];

  for (const element of elements) {
    if (!(element instanceof HTMLElement)) {
      continue;
    }
    const card = element.closest<HTMLElement>('[data-instance-id]');
    if (card?.dataset.instanceId) {
      if (card.dataset.instanceId === draggedInstanceId) {
        continue;
      }
      return { type: 'card', instanceId: card.dataset.instanceId };
    }
    const stack = element.closest<HTMLElement>('[data-playtest-stack-zone-id]');
    const stackZoneId = stack?.dataset.playtestStackZoneId as PlaytestZoneId | undefined;
    if (stackZoneId) {
      return { type: 'zone', zoneId: stackZoneId };
    }
    const zone = element.closest<HTMLElement>('[data-playtest-drop-zone]');
    const zoneId = zone?.dataset.playtestDropZone as PlaytestZoneId | 'board' | undefined;
    if (zoneId) {
      return { type: 'zone', zoneId };
    }
  }

  return null;
};

const completeDraggedGroupDrop = (drag: PlaytestDraggedCard, pending: PointerDragStart): void => {
  if (!playtest.value || !drag.groupInstanceIds?.length) {
    return;
  }
  const dropTarget = resolveDropTarget(drag.pointerX, drag.pointerY, drag.instanceId);
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
  const deltaX = ((drag.pointerX - pending.startX) / bounds.width) * 100;
  const deltaY = ((drag.pointerY - pending.startY) / bounds.height) * 100;
  applyState(moveBoardInstancesByDelta(playtest.value, drag.groupInstanceIds, deltaX, deltaY));
};

const completeDraggedCardDrop = (drag: PlaytestDraggedCard): void => {
  if (!playtest.value) {
    return;
  }
  const dropTarget = resolveDropTarget(drag.pointerX, drag.pointerY, drag.instanceId);
  if (!dropTarget) {
    const position = boardDropPosition(drag);
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
      const position = boardDropPosition(drag) ?? nextBoardPosition();
      applyState(placeInstanceOnBoard(playtest.value, drag.instanceId, position.x, position.y));
      return;
    }
    const targetIndex = getZoneInstances(playtest.value, target.zoneId).findIndex(
      (instance) => instance.instanceId === target.instanceId,
    );
    applyState(moveInstanceToZone(playtest.value, drag.instanceId, target.zoneId, targetIndex));
    return;
  }

  if (dropTarget.zoneId === 'board') {
    const position = boardDropPosition(drag) ?? nextBoardPosition();
    applyState(removeInstanceFromVisualPile(placeInstanceOnBoard(playtest.value, drag.instanceId, position.x, position.y), drag.instanceId));
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
  if (openStackZone.value) {
    closeStack();
  }
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
      candidate: resolveDropTarget(event.clientX, event.clientY, pending.instanceId),
    };
    if (pending.source.type === 'stack') {
      closeStack();
    }
    event.preventDefault();
    return;
  }
  if (activeDrag.value) {
    activeDrag.value = {
      ...activeDrag.value,
      pointerX: event.clientX,
      pointerY: event.clientY,
      ctrlKey: event.ctrlKey,
      candidate: resolveDropTarget(event.clientX, event.clientY, activeDrag.value.instanceId),
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
      candidate: resolveDropTarget(event.clientX, event.clientY, activeDrag.value.instanceId),
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
useEventListener(window, 'pointercancel', finishPointerDrag);

const updateOpeningHandSize = (handSize: number): void => {
  if (!playtest.value) {
    return;
  }
  applyState(setOpeningHandSize(playtest.value, handSize));
};

const toggleOpeningMana = (instanceId: string, selected: boolean): void => {
  if (!playtest.value) {
    return;
  }
  applyState(toggleOpeningManaSelection(playtest.value, instanceId, selected));
};

const toggleOpeningSetup = (instanceId: string, selected: boolean): void => {
  if (!playtest.value) {
    return;
  }
  applyState(toggleOpeningSetupSelection(playtest.value, instanceId, selected));
};

const mulliganOpeningSetup = (): void => {
  if (!playtest.value) {
    return;
  }
  applyState(mulliganOpeningHand(playtest.value));
};

const keepOpeningSetup = (): void => {
  if (!playtest.value) {
    return;
  }
  applyState(acceptOpeningSetup(playtest.value));
};

const drawOne = (): void => {
  if (playtest.value) {
    applyState(drawCards(playtest.value, 1));
  }
};

const nextTurn = (): void => {
  if (playtest.value) {
    applyState(startNextTurn(playtest.value));
  }
};

const drawFromStack = (zoneId: PlaytestZoneId): void => {
  if (Date.now() < suppressClickUntil.value) {
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

const cardActions = (instanceId: string): PlaytestEntityAction[] => {
  const instance = playtest.value?.instances.find((entry) => entry.instanceId === instanceId);
  if (!instance) {
    return [];
  }
  const zoneActions: PlaytestEntityAction[] = [
    { id: 'move-hand', label: 'Move to Hand', disabled: instance.zoneId === 'hand', run: () => moveCardToZone(instanceId, 'hand') },
    { id: 'move-play', label: 'Move to Board', disabled: instance.zoneId === 'play', run: () => moveCardToZone(instanceId, 'play') },
    { id: 'move-discard', label: 'Move to Discard', disabled: instance.zoneId === 'discard', run: () => moveCardToZone(instanceId, 'discard') },
    { id: 'move-banish', label: 'Move to Banish', disabled: instance.zoneId === 'banish', run: () => moveCardToZone(instanceId, 'banish') },
    { id: 'move-library', label: 'Move to Library', disabled: instance.zoneId === 'library', run: () => moveCardToZone(instanceId, 'library') },
    { id: 'move-hero', label: 'Move to Hero', disabled: instance.zoneId === 'hero', run: () => moveCardToZone(instanceId, 'hero') },
  ];
  return [
    ...(instance.zoneId === 'play'
      ? [{ id: 'tap', label: instance.tapped ? 'Untap' : 'Tap', run: () => applyState(toggleTapped(playtest.value as PlaytestState, instanceId)) }]
      : []),
    ...(instance.pileGroupId
      ? [{ id: 'remove-pile', label: 'Remove from Pile', run: () => playtest.value && applyState(removeInstanceFromVisualPile(playtest.value, instanceId)) }]
      : []),
    ...zoneActions,
  ];
};

const stackActions = (zoneId: PlaytestZoneId): PlaytestEntityAction[] => {
  const definition = stackZoneDefinitions.find((zone) => zone.id === zoneId);
  const hasCards = zoneCount(zoneId) > 0;
  const defaultActions: PlaytestEntityAction[] =
    definition?.defaultAction === 'draw'
      ? [
          {
            id: 'stack-default',
            label: 'Draw Top Card',
            disabled: !hasCards,
            run: () => drawFromStack(zoneId),
          },
        ]
      : [];

  return [
    ...defaultActions,
    { id: 'stack-open', label: 'Open Stack', disabled: !hasCards, run: () => openStack(zoneId) },
    { id: 'top-hand', label: 'Move Top to Hand', disabled: !hasCards, run: () => moveTopStackCard(zoneId, 'hand') },
    { id: 'top-play', label: 'Move Top to Board', disabled: !hasCards, run: () => moveTopStackCard(zoneId, 'play') },
    { id: 'top-discard', label: 'Move Top to Discard', disabled: !hasCards || zoneId === 'discard', run: () => moveTopStackCard(zoneId, 'discard') },
    { id: 'top-banish', label: 'Move Top to Banish', disabled: !hasCards || zoneId === 'banish', run: () => moveTopStackCard(zoneId, 'banish') },
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
  applyState(createInitialPlaytestState(deck.value));
};

const loadCurrentCardBack = async (): Promise<void> => {
  try {
    const response = await fetchCurrentCardBack();
    currentCardBackUrl.value = response.current?.image_url ? toAbsoluteApiUrl(response.current.image_url) : null;
  } catch (error) {
    console.error('Current card back could not be loaded', error);
    currentCardBackUrl.value = null;
  }
};

const resumeStaleDraft = (): void => {
  if (!staleDraft.value) {
    return;
  }
  saveSuspended.value = false;
  playtest.value = staleDraft.value.state;
  staleDraft.value = null;
};

const boardCardStyle = (instance: PlaytestCardInstance, index: number): Record<string, string | number> => {
  const x = instance.boardX ?? 16 + (index % 5) * 16;
  const y = instance.boardY ?? 22 + Math.floor(index / 5) * 24;
  return {
    left: `${x}%`,
    top: `${y}%`,
    zIndex: 20 + index,
  };
};

const handCardStyle = (index: number, total: number): Record<string, string | number> => {
  const center = index - (total - 1) / 2;
  return {
    marginLeft: index === 0 ? '0' : 'calc(var(--playtest-card-width) * -0.42)',
    transform: `translateY(${Math.abs(center) * 0.42}rem) rotate(${center * 4.2}deg)`,
    zIndex: 30 + index,
  };
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

useResizeObserver(lowerBarRef, ([entry]) => {
  lowerBarWidth.value = entry?.contentRect.width ?? 0;
});

onMounted(async () => {
  loading.value = true;
  void loadCurrentCardBack();
  try {
    const loadedDeck = await fetchVisibleDeck();
    deck.value = loadedDeck;
    const draft = storage.load(loadedDeck.id);
    if (draft && !isStoredDraftStale(draft, loadedDeck)) {
      playtest.value = draft.state;
      return;
    }
    if (draft) {
      staleDraft.value = draft;
      saveSuspended.value = true;
    }
    playtest.value = createInitialPlaytestState(loadedDeck);
  } finally {
    loading.value = false;
  }
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

.playtester-table {
  --playtest-surface: color-mix(in srgb, var(--color-surface-soft) 78%, var(--app-bg-to) 22%);
  --playtest-surface-accent: color-mix(in srgb, var(--color-control-accent) 10%, transparent);
  --playtest-panel: color-mix(in srgb, var(--color-surface-strong) 88%, transparent);
  --playtest-panel-muted: color-mix(in srgb, var(--color-surface-muted) 82%, transparent);
  --playtest-panel-strong: color-mix(in srgb, var(--color-popover) 94%, transparent);
  --playtest-border: color-mix(in srgb, var(--color-border) 82%, transparent);
  --playtest-grid-line: color-mix(in srgb, var(--color-border) 42%, transparent);
  --playtest-text: var(--color-text);
  --playtest-text-muted: var(--color-text-muted);
  --playtest-text-soft: var(--color-text-soft);
  --playtest-shadow: 0 1.1rem 2.4rem rgba(15, 23, 42, 0.12);
  position: relative;
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background:
    radial-gradient(circle at 18% 0%, var(--playtest-surface-accent), transparent 28%),
    linear-gradient(var(--playtest-grid-line) 1px, transparent 1px),
    linear-gradient(90deg, var(--playtest-grid-line) 1px, transparent 1px),
    var(--playtest-surface);
  background-size: auto, 1.35rem 1.35rem, 1.35rem 1.35rem, auto;
  color: var(--playtest-text);
  box-shadow: var(--playtest-shadow);
}

:global(html.dark) .playtester-table {
  --playtest-surface: #141817;
  --playtest-surface-accent: color-mix(in srgb, var(--color-control-accent) 15%, transparent);
  --playtest-panel: rgba(8, 10, 10, 0.76);
  --playtest-panel-muted: rgba(8, 10, 10, 0.64);
  --playtest-panel-strong: rgba(12, 15, 15, 0.93);
  --playtest-border: rgba(255, 255, 255, 0.08);
  --playtest-grid-line: rgba(255, 255, 255, 0.035);
  --playtest-text: rgba(255, 255, 255, 0.92);
  --playtest-text-muted: rgba(255, 255, 255, 0.82);
  --playtest-text-soft: rgba(255, 255, 255, 0.48);
  --playtest-shadow: 0 1.5rem 4rem rgba(0, 0, 0, 0.24);
}

.playtester-stale,
.playtester-topbar,
.playtester-footer,
.playtester-sideboards {
  position: relative;
  z-index: 30;
}

.playtester-stale {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  margin: 0.75rem;
  padding: 1rem;
  border-radius: 0.75rem;
}

.playtester-topbar {
  display: flex;
  gap: 1rem;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  border-bottom: 1px solid var(--playtest-border);
  background: var(--playtest-panel);
  backdrop-filter: blur(12px);
}

.playtester-board {
  position: relative;
  min-height: 20rem;
  flex: 1 1 auto;
  border-bottom: 1px solid var(--playtest-border);
}

.playtester-board-label,
.playtester-zone-heading,
.playtester-hand-bar,
.playtester-pile-title,
.playtester-pile-count {
  color: var(--playtest-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.playtester-board-label {
  position: absolute;
  top: 0.85rem;
  left: 1rem;
  z-index: 10;
  display: flex;
  gap: 0.7rem;
}

.playtester-board-empty {
  position: absolute;
  inset: 45% auto auto 50%;
  z-index: 1;
  transform: translate(-50%, -50%);
  color: var(--playtest-text-soft);
  font-size: 0.95rem;
  font-weight: 700;
  pointer-events: none;
}

.playtester-board-card {
  position: absolute;
  transform: translate(-50%, -50%);
}

.playtester-selection-box {
  position: absolute;
  z-index: 35;
  border: 2px solid color-mix(in srgb, var(--color-accent) 76%, white 24%);
  background: color-mix(in srgb, var(--color-accent) 28%, transparent);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.34),
    inset 0 0 0 1px rgba(0, 0, 0, 0.22),
    0 0.5rem 1.5rem rgba(0, 0, 0, 0.22);
  pointer-events: none;
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

.playtester-lower {
  position: relative;
  z-index: 30;
  display: flex;
  align-items: stretch;
  flex: 0 0 auto;
  gap: 0.75rem;
  overflow: hidden;
  padding: 0.75rem;
  border-top: 1px solid var(--playtest-border);
  background: var(--playtest-panel-muted);
  backdrop-filter: blur(12px);
}

.playtester-hand {
  flex: 1 1 34rem;
  min-width: 0;
  min-height: calc((var(--playtest-card-width, 9.75rem) * 1.42) + 3.4rem);
  overflow: hidden;
  border-right: 1px solid var(--playtest-border);
}

.playtester-hand-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.8rem 0;
}

.playtester-hand-fan {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-width: max-content;
  padding: 1.25rem 1.5rem 0.75rem;
}

.playtester-hand-card {
  flex: 0 0 auto;
  transition:
    transform 180ms ease,
    margin 180ms ease;
}

.playtester-piles {
  display: flex;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 0.75rem;
}

.playtester-stack-popover {
  position: absolute;
  right: 1rem;
  bottom: 5.5rem;
  z-index: 40;
  width: min(48rem, calc(100% - 2rem));
}

.playtester-stack-panel {
  max-height: min(36rem, calc(100vh - 12rem));
  overflow: hidden;
  border: 1px solid var(--playtest-border);
  border-radius: 0.9rem;
  background: var(--playtest-panel-strong);
  box-shadow: 0 2rem 5rem rgba(15, 23, 42, 0.22);
}

.playtester-stack-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border-bottom: 1px solid var(--playtest-border);
}

.playtester-stack-panel-header h3 {
  color: var(--playtest-text);
  font-size: 1rem;
  font-weight: 800;
}

.playtester-stack-panel-header p {
  color: var(--playtest-text-soft);
  font-size: 0.82rem;
  font-weight: 700;
}

.playtester-stack-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--playtest-card-width, 9.75rem), 1fr));
  max-height: min(28rem, calc(100vh - 19rem));
  gap: 1rem;
  overflow: auto;
  padding: 1rem;
}

.playtester-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.75rem;
  border-top: 1px solid var(--playtest-border);
  background: var(--playtest-panel);
  backdrop-filter: blur(12px);
}

.playtester-scale {
  width: 8rem;
  accent-color: var(--color-accent);
}

.playtester-sideboards {
  padding: 0 0.75rem 0.75rem;
}

.playtester-sideboards summary {
  cursor: pointer;
  color: var(--playtest-text-muted);
  font-size: 0.85rem;
  font-weight: 700;
}

@media (max-width: 1279px) {
  .playtester-lower {
    align-items: stretch;
  }
}

@media (max-width: 767px) {
  .playtester-topbar,
  .playtester-footer,
  .playtester-stale {
    align-items: stretch;
    flex-direction: column;
  }

  .playtester-board {
    min-height: 22rem;
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

  .playtester-stack-popover {
    right: 0.75rem;
    bottom: 6rem;
    width: calc(100% - 1.5rem);
  }
}
</style>
