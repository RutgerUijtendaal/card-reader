<template>
  <aside class="page-card flex h-full min-h-0 flex-col overflow-hidden p-0">
    <template v-if="controller.deck.isSetupStep.value">
      <div class="app-scrollbar flex-1 space-y-4 overflow-y-auto p-5 pr-4">
        <div class="space-y-1">
          <h3 class="theme-section-title text-lg font-semibold">
            Deck Setup
          </h3>
          <p class="theme-section-muted text-sm">
            Enter the deck details and choose a hero.
          </p>
        </div>

        <label class="field-label">
          Name
          <input
            v-model="deckName"
            class="input-base"
            placeholder="Deck name"
          >
        </label>

        <label class="field-label">
          Description
          <textarea
            v-model="deckDescription"
            class="input-base min-h-28"
            placeholder="Optional description"
          />
        </label>

        <div class="space-y-2">
          <p class="theme-section-title text-sm font-semibold">
            Visibility
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="option in visibilityOptions"
              :key="option.value"
              class="theme-pill text-xs"
              :class="visibility === option.value ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="updateDeckVisibility(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="theme-section-muted text-xs">
            {{ selectedVisibilityDescription }}
          </p>
        </div>

        <div class="theme-muted-panel space-y-3 p-3">
          <p class="theme-section-title text-sm font-semibold">
            Selected Hero
          </p>
          <div
            v-if="controller.deck.selectedHero.value"
            class="space-y-3"
          >
            <img
              v-if="controller.deck.selectedHero.value.image_url"
              :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
              :alt="controller.deck.selectedHero.value.name"
              class="theme-card-frame max-h-80 w-full rounded-2xl object-contain"
            >
            <div
              v-else
              class="theme-empty-state flex h-52 items-center justify-center rounded-2xl text-sm"
            >
              No hero image
            </div>

            <div class="space-y-1">
              <p class="theme-section-title text-sm font-semibold">
                {{ controller.deck.selectedHero.value.name }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ controller.deck.selectedHero.value.label }}
              </p>
            </div>
          </div>
          <p
            v-else
            class="theme-section-muted text-sm"
          >
            No hero selected.
          </p>
        </div>

        <div
          v-if="controller.deck.setupMessages.value.length > 0"
          class="theme-muted-panel space-y-2 p-3"
        >
          <p class="theme-section-title text-sm font-semibold">
            Missing Setup
          </p>
          <p
            v-for="message in controller.deck.setupMessages.value"
            :key="message"
            class="theme-error-text text-sm"
          >
            {{ message }}
          </p>
        </div>

        <button
          class="btn-primary w-full justify-center"
          type="button"
          :disabled="controller.deck.setupMessages.value.length > 0"
          @click="controller.lockSetup"
        >
          Continue
        </button>
      </div>
    </template>

    <template v-else>
      <div
        class="z-20 space-y-3"
        data-testid="deck-summary-top"
      >
        <section
          ref="heroDetailsTriggerRef"
          class="theme-card-frame rounded-t-xl"
        >
          <div
            class="relative"
          >
            <div
              v-if="controller.deck.selectedHero.value?.image_url"
              class="absolute inset-0"
            >
              <img
                :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
                :alt="controller.deck.selectedHero.value.name"
                class="h-full w-full object-cover"
                :style="{
                  objectPosition: heroHeaderObjectPosition,
                  transform: heroHeaderTransform,
                  opacity: heroHeaderOpacity,
                }"
              >
            </div>
            <div
              v-else
              class="absolute inset-0 theme-card-frame-muted"
            />
            <div class="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-slate-900/74 to-slate-900/28" />

            <div class="relative flex min-h-[5.5rem] items-start gap-2 px-4 py-3">
              <button
                type="button"
                class="flex min-w-0 flex-1 items-start gap-3 text-left"
                @click="toggleHeroDetails()"
              >
                <div class="min-w-0 space-y-1">
                  <p class="truncate text-lg font-semibold text-white">
                    {{ controller.deck.form.name || 'Untitled Deck' }}
                  </p>
                  <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-100/90">
                    <span class="font-semibold uppercase tracking-[0.18em] text-slate-200/70">{{ activeBoardLabel }}</span>
                    <span class="font-semibold">{{ activeBoardCount }}</span>
                    <span
                      v-if="controller.deck.selectedHero.value"
                      class="truncate"
                    >
                      {{ controller.deck.selectedHero.value.name }}
                    </span>
                  </div>
                </div>
              </button>

              <button
                class="btn-secondary inline-flex h-8 shrink-0 items-center justify-center px-3 py-0 text-xs"
                type="button"
                @click="controller.setBuilderStep('setup')"
              >
                Change
              </button>

              <button
                type="button"
                class="theme-card-frame-muted theme-section-title inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition"
                :aria-label="heroDetailsExpanded ? 'Collapse hero details' : 'Expand hero details'"
                @click="toggleHeroDetails()"
              >
                <ChevronDown
                  class="h-4 w-4 transition-transform"
                  :class="heroDetailsExpanded ? 'rotate-180' : ''"
                />
              </button>
            </div>
          </div>
        </section>

        <div class="space-y-3 px-5">
          <div
            v-if="controller.deck.validationMessages.value.length > 0"
            class="theme-muted-panel space-y-2 p-3"
          >
            <p class="theme-section-title text-sm font-semibold">
              Validation
            </p>
            <p
              v-for="message in controller.deck.validationMessages.value"
              :key="message"
              class="theme-error-text text-sm"
            >
              {{ message }}
            </p>
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between gap-3">
              <h4 class="theme-section-title text-sm font-semibold">
                Deck Boards
              </h4>
              <button
                class="btn-secondary inline-flex h-8 shrink-0 items-center gap-1.5 px-3 py-0 text-xs"
                type="button"
                @click="controller.deck.addSideboard()"
              >
                <Plus class="h-3.5 w-3.5" />
                Add Sideboard
              </button>
            </div>

            <div
              v-if="controller.deck.sideboardTabs.value.length > 0"
              class="flex min-h-8 flex-wrap items-center gap-2"
            >
              <button
                class="theme-pill text-xs"
                :class="controller.deck.activeBoardId.value === 'mainboard' ? 'theme-pill-accent' : 'theme-pill-neutral'"
                type="button"
                @click="controller.deck.selectBoard('mainboard')"
              >
                Mainboard ({{ controller.deck.totalMainboardCards.value }})
              </button>
              <div
                v-for="sideboard in controller.deck.sideboardTabs.value"
                :key="sideboard.id"
                class="inline-flex items-center"
                @mouseenter="hoveredSideboardId = sideboard.id"
                @mouseleave="clearHoveredSideboard(sideboard.id)"
                @focusin="focusedSideboardId = sideboard.id"
                @focusout="handleSideboardFocusOut($event, sideboard.id)"
              >
                <button
                  v-if="editingSideboardId !== sideboard.id"
                  class="theme-pill text-xs"
                  :class="controller.deck.activeBoardId.value === sideboard.id ? 'theme-pill-accent' : 'theme-pill-neutral'"
                  type="button"
                  @click="selectSideboard(sideboard.id)"
                >
                  <span class="truncate">
                    {{ sideboard.name }} ({{ sideboard.totalCards }})
                  </span>
                </button>
                <div
                  v-else
                  class="theme-pill theme-pill-accent inline-flex items-center px-2 py-1"
                >
                  <input
                    :ref="setEditingSideboardInputRef"
                    v-model="editingSideboardName"
                    class="min-w-[7rem] bg-transparent text-xs font-medium outline-none"
                    :aria-label="`Rename ${sideboard.name}`"
                    @click.stop
                    @keydown.enter.prevent="commitRenameSideboard()"
                    @keydown.esc.prevent="cancelRenameSideboard()"
                    @blur="commitRenameSideboard()"
                  >
                </div>

                <button
                  v-if="shouldShowSideboardActions(sideboard.id)"
                  class="theme-card-frame-muted theme-section-title -ml-1 inline-flex h-7 w-7 items-center justify-center rounded-full"
                  type="button"
                  :aria-label="`Open sideboard actions for ${sideboard.name}`"
                  @click="openSideboardActions($event, sideboard.id)"
                >
                  <Ellipsis class="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <Teleport to="body">
        <div
          v-if="sideboardActionsOpen && sideboardActionsTargetId"
          ref="sideboardActionsPanelRef"
          class="theme-popover z-40 w-44 p-2"
          :style="{
            position: 'fixed',
            left: `${sideboardActionsX}px`,
            top: `${sideboardActionsY}px`,
          }"
        >
          <div class="space-y-1">
            <button
              type="button"
              class="btn-secondary w-full justify-start gap-2 px-3 py-2 text-xs"
              @click="beginRenameSideboard(
                sideboardActionsTargetId,
                controller.deck.sideboardTabs.value.find((sideboard) => sideboard.id === sideboardActionsTargetId)?.name ?? '',
              )"
            >
              <Pencil class="h-3.5 w-3.5" />
              Rename
            </button>
            <button
              type="button"
              class="btn-danger-secondary w-full justify-start gap-2 px-3 py-2 text-xs"
              @click="promptDeleteSideboard(
                sideboardActionsTargetId,
                controller.deck.sideboardTabs.value.find((sideboard) => sideboard.id === sideboardActionsTargetId)?.name ?? 'sideboard',
              )"
            >
              <Trash2 class="h-3.5 w-3.5" />
              Delete
            </button>
          </div>
        </div>
      </Teleport>

      <Teleport to="body">
        <div
          v-if="heroDetailsExpanded"
          ref="heroDetailsPanelRef"
          class="theme-popover z-30 p-4 shadow-2xl"
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
              class="theme-card-frame-muted mx-auto w-full max-w-[22rem] overflow-hidden rounded-2xl"
            >
              <img
                :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
                :alt="controller.deck.selectedHero.value.name"
                class="h-full w-full object-cover object-top"
              >
            </div>
            <div
              v-else
              class="theme-empty-state mx-auto flex h-[31rem] w-full max-w-[22rem] items-center justify-center rounded-2xl text-sm"
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
        class="app-scrollbar relative z-10 mt-4 flex-1 min-h-0 overflow-y-auto px-5 pb-5 pr-4"
        data-testid="deck-summary-list"
      >
        <div class="space-y-3 pb-1">
          <div
            v-if="controller.deck.detailedActiveBoardEntries.value.length === 0"
            class="theme-empty-state"
          >
            No cards added to this board yet.
          </div>

          <DeckBuilderBoardEntryRow
            v-for="entry in controller.deck.detailedActiveBoardEntries.value"
            :key="entry.card.id"
            :entry="entry"
            :hover-mode="controller.filters.hoverMode.value"
            :quantity-max="controller.deck.getCardQuantityLimit(entry.card.id)"
            :move-destinations="getMoveDestinations(entry.card.id)"
            :row-action-disabled="controller.deck.boardRowActionDisabled(entry.card.id)"
            :row-secondary-action-disabled="controller.deck.boardRowSecondaryActionDisabled(entry.card.id)"
            @decrement="controller.deck.changeQuantity($event, -1)"
            @increment="controller.deck.changeQuantity($event, 1)"
            @remove="controller.deck.removeEntry"
            @row-action="controller.deck.handleBoardRowAction"
            @row-secondary-action="controller.deck.handleBoardRowSecondaryAction"
            @move-to-board="handleMoveToBoard"
          />
        </div>
      </div>

      <ConfirmModal
        :open="deleteSideboardTarget !== null"
        title="Delete Sideboard"
        :message="deleteSideboardTarget ? `Delete sideboard '${deleteSideboardTarget.name}'?` : ''"
        confirm-label="Delete"
        cancel-label="Cancel"
        @cancel="deleteSideboardTarget = null"
        @confirm="confirmDeleteSideboard"
      />
    </template>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { ChevronDown, Ellipsis, Pencil, Plus, Trash2 } from 'lucide-vue-next';
import { toAbsoluteApiUrl } from '@/api/client';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import DeckBuilderBoardEntryRow from '@/modules/decks/components/DeckBuilderBoardEntryRow.vue';
import DeckManaCurve from '@/modules/decks/components/DeckManaCurve.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';
import type { DeckBoardMoveDestination } from '@/modules/decks/composables/useDeckEditorDraft';
import type { DeckVisibility } from '@/modules/decks/types';
import { deckVisibilityDescriptions, deckVisibilityOptions } from '@/modules/decks/visibility';

const props = defineProps<{
  controller: DeckEditorController;
}>();

const deckName = computed({
  get: () => props.controller.deck.form.name,
  set: props.controller.deck.setDeckName,
});

const deckDescription = computed({
  get: () => props.controller.deck.form.description,
  set: props.controller.deck.setDeckDescription,
});

const visibilityOptions = deckVisibilityOptions;
const visibility = computed(() => props.controller.deck.form.visibility);
const selectedVisibilityDescription = computed(() => deckVisibilityDescriptions[visibility.value] ?? '');
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
const {
  isOpen: sideboardActionsOpen,
  triggerRef: sideboardActionsTriggerRef,
  panelRef: sideboardActionsPanelRef,
  x: sideboardActionsX,
  y: sideboardActionsY,
  toggle: toggleSideboardActions,
  close: closeSideboardActions,
} = useFloatingPopover({
  placement: 'bottom-end',
});
const sideboardActionsTargetId = ref<string | null>(null);
const editingSideboardId = ref<string | null>(null);
const editingSideboardName = ref('');
const editingSideboardInputRef = ref<HTMLInputElement | null>(null);
const deleteSideboardTarget = ref<{ id: string; name: string } | null>(null);
const hoveredSideboardId = ref<string | null>(null);
const focusedSideboardId = ref<string | null>(null);

const activeBoardLabel = computed(() =>
  props.controller.deck.activeBoardId.value === 'mainboard'
    ? 'Mainboard'
    : (props.controller.deck.activeSideboard.value?.name.trim() || 'Sideboard'),
);
const activeBoardCount = computed(() =>
  props.controller.deck.activeBoardId.value === 'mainboard'
    ? props.controller.deck.totalMainboardCards.value
    : (props.controller.deck.activeSideboard.value?.entries.reduce((sum, entry) => sum + entry.quantity, 0) ?? 0),
);
const heroHeaderObjectPosition = '30% 10%';
const heroHeaderTransform = 'scale(1.28)';
const heroHeaderOpacity = 0.75;

const updateDeckVisibility = (value: DeckVisibility): void => {
  props.controller.deck.setDeckVisibility(value);
};

const selectSideboard = (sideboardId: string): void => {
  if (editingSideboardId.value === sideboardId) {
    return;
  }
  props.controller.deck.selectBoard(sideboardId);
};

const getMoveDestinations = (cardId: string): DeckBoardMoveDestination[] =>
  props.controller.deck.getBoardMoveDestinations(cardId);

const handleMoveToBoard = (cardId: string, destinationBoardId: string): void => {
  props.controller.deck.moveEntryToBoard(cardId, destinationBoardId);
};

const setEditingSideboardInputRef = (element: unknown): void => {
  editingSideboardInputRef.value = element instanceof HTMLInputElement ? element : null;
};

const openSideboardActions = (event: MouseEvent, sideboardId: string): void => {
  event.stopPropagation();
  sideboardActionsTriggerRef.value = event.currentTarget as HTMLElement | null;
  if (sideboardActionsOpen.value && sideboardActionsTargetId.value === sideboardId) {
    closeSideboardActions();
    sideboardActionsTargetId.value = null;
    return;
  }

  sideboardActionsTargetId.value = sideboardId;
  if (sideboardActionsOpen.value) {
    closeSideboardActions();
  }
  toggleSideboardActions();
};

const clearHoveredSideboard = (sideboardId: string): void => {
  if (hoveredSideboardId.value === sideboardId) {
    hoveredSideboardId.value = null;
  }
};

const handleSideboardFocusOut = (event: FocusEvent, sideboardId: string): void => {
  const currentTarget = event.currentTarget;
  if (!(currentTarget instanceof HTMLElement)) {
    return;
  }
  const nextTarget = event.relatedTarget as Node | null;
  if (nextTarget && currentTarget.contains(nextTarget)) {
    return;
  }
  if (focusedSideboardId.value === sideboardId) {
    focusedSideboardId.value = null;
  }
};

const shouldShowSideboardActions = (sideboardId: string): boolean => {
  if (editingSideboardId.value === sideboardId) {
    return false;
  }
  if (sideboardActionsOpen.value && sideboardActionsTargetId.value === sideboardId) {
    return true;
  }
  return hoveredSideboardId.value === sideboardId || focusedSideboardId.value === sideboardId;
};

const beginRenameSideboard = async (sideboardId: string, name: string): Promise<void> => {
  closeSideboardActions();
  sideboardActionsTargetId.value = null;
  editingSideboardId.value = sideboardId;
  editingSideboardName.value = name;
  await nextTick();
  editingSideboardInputRef.value?.focus();
  editingSideboardInputRef.value?.select();
};

const cancelRenameSideboard = (): void => {
  editingSideboardId.value = null;
  editingSideboardName.value = '';
};

const commitRenameSideboard = (): void => {
  if (!editingSideboardId.value) {
    return;
  }
  const nextName = editingSideboardName.value.trim();
  if (!nextName) {
    cancelRenameSideboard();
    return;
  }

  props.controller.deck.renameSideboard(editingSideboardId.value, nextName);
  cancelRenameSideboard();
};

const promptDeleteSideboard = (sideboardId: string, name: string): void => {
  closeSideboardActions();
  sideboardActionsTargetId.value = null;
  deleteSideboardTarget.value = { id: sideboardId, name };
};

const confirmDeleteSideboard = (): void => {
  if (!deleteSideboardTarget.value) {
    return;
  }
  if (props.controller.deck.activeBoardId.value === deleteSideboardTarget.value.id) {
    props.controller.deck.selectBoard('mainboard');
  }
  props.controller.deck.removeSideboard(deleteSideboardTarget.value.id);
  deleteSideboardTarget.value = null;
};
</script>
