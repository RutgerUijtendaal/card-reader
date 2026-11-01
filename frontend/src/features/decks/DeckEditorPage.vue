<template>
  <section
    class="flex flex-col gap-6"
    :aria-busy="controller.isCreating.value"
  >
    <AppPageHeader
      :icon="APP_SECTION_ICONS.deckBuilder"
      :title="deckTitle"
      :subtitle="deckEditorSubtitle"
      :back-to="controller.isCreating.value ? null : controller.backLink.value"
      :back-label="controller.backLabel.value"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <div
          class="deck-editor-header-divider theme-divider hidden h-6 border-l lg:block"
          aria-hidden="true"
        />
        <div class="flex items-center gap-2">
          <AppHeaderAction
            v-if="!controller.isPublished.value && controller.hasLocalDraft.value"
            :icon="Trash2"
            label="Discard local draft"
            short-label="Discard"
            :disabled="controller.isMutationLocked.value"
            @click="controller.requestDiscardLocalDraft()"
          />
          <AppHeaderAction
            :icon="deckSaveActionIcon"
            :label="deckSaveActionLabel"
            :short-label="deckSaveActionShortLabel"
            variant="primary"
            :icon-class="deckSaveActionPending ? 'animate-spin' : ''"
            :disabled="deckSaveActionDisabled"
            @click="() => controller.saveDeck()"
          />
        </div>
      </template>
      <template
        v-if="!controller.loading.value"
        #bottomLeft
      >
        <DeckBuilderFilterBar :controller="controller" />
      </template>
    </AppPageHeader>

    <BuilderWorkspaceLayout :inert="controller.isMutationLocked.value">
      <DeckBuilderGallery
        :controller="controller"
        :loading="controller.loading.value"
      />
      <template
        v-if="isDetailsOpen"
        #overlay
      >
        <section
          class="mx-auto w-full max-w-4xl px-5 pb-10 pt-4"
          aria-label="Deck details"
          @keydown.esc="controller.closeDetails()"
        >
          <div class="sticky top-0 z-10 -mx-1 flex justify-end bg-[var(--table-canvas)] py-2">
            <button
              class="theme-icon-button inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--color-border-strong)]"
              type="button"
              aria-label="Close deck details"
              title="Close details"
              @click="controller.closeDetails()"
            >
              <X
                class="h-4 w-4"
                aria-hidden="true"
              />
            </button>
          </div>
          <div
            v-if="controller.loading.value"
            class="space-y-5"
            aria-hidden="true"
          >
            <div class="deck-builder-loading-line h-11 w-full" />
            <div class="deck-builder-loading-line h-20 w-full" />
            <div class="deck-builder-loading-line h-64 w-full" />
          </div>
          <DeckDetailsForm
            v-else
            :controller="controller"
          />
        </section>
      </template>
      <template #endAside>
        <aside
          v-if="controller.loading.value"
          class="app-sticky-aside app-sticky-aside-right deck-builder-loading-panel"
        >
          <div class="app-sticky-aside-scroll space-y-5">
            <div class="space-y-3">
              <div class="deck-builder-loading-line h-4 w-36" />
              <div class="deck-builder-loading-line h-8 w-full" />
            </div>
            <div
              v-for="sectionIndex in 3"
              :key="`loading-board-${sectionIndex}`"
              class="space-y-2"
            >
              <div class="deck-builder-loading-line h-4 w-24" />
              <div
                v-for="rowIndex in 4"
                :key="`loading-board-${sectionIndex}-${rowIndex}`"
                class="deck-builder-loading-line h-11 w-full"
              />
            </div>
          </div>
        </aside>
        <DeckBuilderSummaryPanel
          v-else
          :controller="controller"
        />
      </template>
      <template #status>
        <section
          v-if="controller.loading.value"
          class="deck-builder-status-bar mx-px flex shrink-0 items-center justify-between gap-4 px-4 py-3"
          aria-hidden="true"
        >
          <div class="flex items-center gap-3">
            <div class="deck-builder-loading-line h-4 w-4 rounded-full" />
            <div class="deck-builder-loading-line h-4 w-32" />
          </div>
          <div class="flex flex-wrap items-center justify-end gap-4">
            <div
              v-for="index in 5"
              :key="`loading-stat-${index}`"
              class="deck-builder-loading-line h-5 w-16"
            />
          </div>
        </section>
        <BuilderStatusBar
          v-else
          aria-label="Deck builder status"
        >
          <BuilderSaveStatus
            v-model:autosync="controller.autosyncEnabled.value"
            :busy="controller.saving.value || controller.creationState.value.status === 'creating'"
            :dirty="controller.hasUnsavedChanges.value"
            :label="controller.changeStatusLabel.value"
            :saved="controller.isPublished.value"
            :can-autosync="controller.canAutosync.value"
          />

          <div class="flex flex-wrap items-center justify-start gap-x-5 gap-y-2 lg:min-w-0 lg:flex-1 lg:justify-end">
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Total</span>
              <span class="theme-section-title theme-display text-lg tabular-nums">{{
                controller.deck.overallTotalCards.value
              }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Main</span>
              <span class="theme-section-title theme-display text-lg tabular-nums">
                {{ controller.deck.totalMainboardCards.value
                }}<template v-if="controller.deck.totalMainboardCards.value >= mainboardMaxCards">
                  / {{ mainboardMaxCards }}</template>
              </span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Mana</span>
              <span class="theme-section-title theme-display text-lg tabular-nums">{{
                controller.deck.totalMainboardManaTypeCards.value
              }}</span>
              <InfoTooltip
                text="If at least 25% of your deck is Mana cards, you can mulligan anytime you draw a starting hand with 0 mana cards."
                placement="bottom"
                :allow-flip="false"
              >
                <CircleCheckBig
                  v-if="controller.deck.hasFreeMulliganManaRatio.value"
                  class="theme-success-text h-4 w-4"
                />
                <CircleX
                  v-else
                  class="theme-error-text h-4 w-4"
                />
              </InfoTooltip>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />

            <div
              v-if="controller.deck.headerDeckTypeCounts.value.length > 0"
              class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm"
            >
              <span class="theme-kicker shrink-0 text-[11px] font-semibold uppercase tracking-wide">Type Mix</span>
              <span
                v-for="row in controller.deck.headerDeckTypeCounts.value"
                :key="row.type.id"
                class="theme-section-muted"
              >
                <span class="theme-section-title font-medium">{{ row.type.label }}</span>
                {{ row.count }}
              </span>
              <span
                v-if="controller.deck.remainingDeckTypeCount.value > 0"
                class="theme-section-muted"
              >
                +{{ controller.deck.remainingDeckTypeCount.value }} more
              </span>
            </div>
            <p
              v-else
              class="theme-section-muted flex items-center gap-2 text-xs"
            >
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Type Mix</span>
              <span>No type data yet.</span>
            </p>

            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div
              v-if="hardIssueMessages.length > 0"
              class="inline-flex"
            >
              <button
                ref="hardIssueTriggerRef"
                class="theme-pill theme-pill-danger inline-flex items-center gap-1.5 px-2 py-1 text-xs font-semibold"
                type="button"
                aria-label="Show deck validity issues"
                :aria-expanded="hardIssuesOpen"
                @mouseenter="hardIssuesOpen = true"
                @mouseleave="hardIssuesOpen = false"
                @focusin="hardIssuesOpen = true"
                @focusout="hardIssuesOpen = false"
              >
                <TriangleAlert class="h-3.5 w-3.5" />
                {{ hardIssueMessages.length }}
              </button>
              <Teleport to="body">
                <div
                  v-if="hardIssuesOpen"
                  ref="hardIssuePanelRef"
                  class="theme-popover pointer-events-none z-50 w-72 p-3 text-sm"
                  role="tooltip"
                  :style="{ position: 'fixed', left: `${hardIssueX}px`, top: `${hardIssueY}px` }"
                >
                  <p class="theme-section-title font-semibold">
                    Issues
                  </p>
                  <ul class="mt-2 space-y-2">
                    <li
                      v-for="message in hardIssueMessages"
                      :key="message"
                      class="theme-section-muted"
                    >
                      {{ message }}
                    </li>
                  </ul>
                </div>
              </Teleport>
            </div>
            <div
              v-if="hardIssueMessages.length > 0"
              class="theme-divider hidden h-4 border-l lg:block"
            />
            <div
              v-if="controller.deck.warningMessages.value.length > 0"
              class="inline-flex"
            >
              <button
                ref="warningTriggerRef"
                class="theme-pill theme-pill-warning inline-flex items-center gap-1.5 px-2 py-1 text-xs font-semibold"
                type="button"
                aria-label="Show deck warnings"
                :aria-expanded="warningsOpen"
                @mouseenter="warningsOpen = true"
                @mouseleave="warningsOpen = false"
                @focusin="warningsOpen = true"
                @focusout="warningsOpen = false"
              >
                <TriangleAlert class="h-3.5 w-3.5" />
                {{ controller.deck.warningMessages.value.length }}
              </button>
              <Teleport to="body">
                <div
                  v-if="warningsOpen"
                  ref="warningPanelRef"
                  class="theme-popover pointer-events-none z-50 w-72 p-3 text-sm"
                  role="tooltip"
                  :style="{ position: 'fixed', left: `${warningX}px`, top: `${warningY}px` }"
                >
                  <p class="theme-section-title font-semibold">
                    Warnings
                  </p>
                  <ul class="mt-2 space-y-2">
                    <li
                      v-for="message in controller.deck.warningMessages.value"
                      :key="message"
                      class="theme-section-muted"
                    >
                      {{ message }}
                    </li>
                  </ul>
                </div>
              </Teleport>
            </div>
            <div
              v-if="controller.deck.warningMessages.value.length > 0"
              class="theme-divider hidden h-4 border-l lg:block"
            />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Unique</span>
              <span class="theme-section-title theme-display text-lg tabular-nums">{{
                controller.deck.overallUniqueCards.value
              }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Status</span>
              <span
                class="text-base font-semibold"
                :class="
                  controller.deck.isDeckValid.value ? 'theme-success-text' : 'theme-section-title'
                "
              >
                {{ controller.deck.deckStatusLabel.value }}
              </span>
            </div>
          </div>
        </BuilderStatusBar>
      </template>
    </BuilderWorkspaceLayout>

    <ConfirmModal
      :open="controller.discardChangesModalOpen.value"
      :title="controller.isPublished.value ? 'Discard deck changes?' : 'Leave local deck draft?'"
      :message="deckLeaveConfirmationMessage"
      :confirm-label="deckLeaveConfirmationLabel"
      cancel-label="Stay Here"
      @confirm="controller.confirmDiscardChanges"
      @cancel="controller.cancelDiscardChanges"
    />
    <ConfirmModal
      :open="controller.discardLocalDraftModalOpen.value"
      title="Discard local deck draft?"
      message="This permanently removes the unpublished deck from this browser."
      confirm-label="Discard Draft"
      cancel-label="Keep Draft"
      @confirm="controller.confirmDiscardLocalDraft"
      @cancel="controller.cancelDiscardLocalDraft"
    />
    <DeckDraftRecoveryModal
      :open="controller.localDraftRecoveryModalOpen.value"
      :saved-at="controller.pendingLocalDraft.value?.savedAt"
      :busy="controller.recoveryActionPending.value"
      @resume="controller.resumeLocalDraft"
      @discard="controller.discardPendingLocalDraft"
    />
    <DeckDraftConflictModal
      :open="controller.localDraftConflictModalOpen.value"
      :kind="controller.localDraftConflict.value?.kind"
      :busy="controller.conflictActionsLocked.value"
      @use-stored="handleUseStoredConflict"
      @keep-local="handleKeepLocalConflict"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  CircleCheckBig,
  CircleX,
  X,
  LoaderCircle,
  Save,
  Trash2,
  TriangleAlert,
} from 'lucide-vue-next';
import BuilderWorkspaceLayout from '@/shared/components/builders/BuilderWorkspaceLayout.vue';
import BuilderStatusBar from '@/shared/components/builders/BuilderStatusBar.vue';
import BuilderSaveStatus from '@/shared/components/builders/BuilderSaveStatus.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';
import ConfirmModal from '@/shared/components/modals/ConfirmModal.vue';
import DeckBuilderFilterBar from '@/features/decks/components/DeckBuilderFilterBar.vue';
import DeckBuilderGallery from '@/features/decks/components/DeckBuilderGallery.vue';
import DeckBuilderSummaryPanel from '@/features/decks/components/DeckBuilderSummaryPanel.vue';
import DeckDetailsForm from '@/features/decks/components/DeckDetailsForm.vue';
import DeckDraftRecoveryModal from '@/shared/components/builders/BuilderDraftRecoveryModal.vue';
import DeckDraftConflictModal from '@/shared/components/builders/BuilderDraftConflictModal.vue';
import { useDeckEditor } from '@/features/decks/composables/useDeckEditor';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';

const controller = useDeckEditor();
const {
  isOpen: hardIssuesOpen,
  triggerRef: hardIssueTriggerRef,
  panelRef: hardIssuePanelRef,
  x: hardIssueX,
  y: hardIssueY,
} = useFloatingPopover({ placement: 'bottom', allowFlip: false });
const {
  isOpen: warningsOpen,
  triggerRef: warningTriggerRef,
  panelRef: warningPanelRef,
  x: warningX,
  y: warningY,
} = useFloatingPopover({ placement: 'bottom', allowFlip: false });
const mainboardMinCards = computed(
  () => controller.deckBuildingRules.value.mainboard_card_count.min ?? 0,
);
const mainboardMaxCards = computed(
  () => controller.deckBuildingRules.value.mainboard_card_count.max ?? 0,
);
const manaMinCards = computed(() => controller.deckBuildingRules.value.mana_type_count.min ?? 0);
const hardIssueMessages = computed(() => controller.deck.validationMessages.value);
const deckSaveActionIcon = computed(() => {
  if (controller.manualSaving.value || controller.creationState.value.status === 'creating') {
    return LoaderCircle;
  }
  return controller.isPublished.value ? Save : APP_SECTION_ICONS.deckBuilder;
});
const deckSaveActionLabel = computed(() => {
  if (controller.terminalNavigationPending.value) {
    return 'Continue after confirmed deck outcome';
  }
  if (controller.creationState.value.status === 'unknown') {
    return 'Retry deck creation';
  }
  if (controller.manualSaving.value || controller.creationState.value.status === 'creating') {
    return controller.isPublished.value ? 'Saving deck' : 'Creating deck';
  }
  return controller.isPublished.value ? 'Save deck' : 'Create deck';
});
const deckSaveActionShortLabel = computed(() => {
  if (controller.terminalNavigationPending.value) return 'Continue';
  if (controller.creationState.value.status === 'unknown') return 'Retry';
  return controller.isPublished.value ? 'Save' : 'Create';
});
const deckSaveActionPending = computed(
  () => controller.manualSaving.value
    || controller.creationState.value.status === 'creating'
    || controller.terminalNavigationInFlight.value,
);
const deckSaveActionDisabled = computed(() => {
  if (controller.isPublished.value) return controller.manualSaving.value;
  if (controller.terminalNavigationPending.value) {
    return controller.terminalNavigationInFlight.value;
  }
  if (controller.creationState.value.status === 'unknown') return false;
  return controller.isMutationLocked.value;
});
const deckLeaveConfirmationMessage = computed(() => {
  if (controller.isPublished.value) {
    return 'You have unsaved deck changes. Leaving this page will discard them.';
  }
  if (controller.localDraftPersistenceFailed.value) {
    return 'This draft could not be saved in this browser. Leaving now will discard your current progress.';
  }
  if (controller.localDraftConflict.value) {
    return 'Another tab changed the browser draft. Leaving now discards this tab and keeps the stored version.';
  }
  if (controller.creationState.value.status === 'unknown') {
    return 'Deck creation could not be confirmed. Leaving keeps the attempted draft in this browser; Retry will use the same request.';
  }
  return 'Your unpublished deck will remain saved in this browser so you can resume it later.';
});
const deckLeaveConfirmationLabel = computed(() => {
  if (controller.isPublished.value) {
    return 'Discard Changes';
  }
  if (controller.localDraftConflict.value) return 'Discard This Tab';
  return controller.localDraftPersistenceFailed.value ? 'Discard & Leave' : 'Leave Draft';
});
const handleUseStoredConflict = (): void => {
  const conflict = controller.localDraftConflict.value;
  if (conflict?.kind === 'active-draft') {
    void controller.loadStoredConflictDraft();
  } else if (conflict?.kind === 'created-elsewhere') {
    void controller.openCreatedConflictDeck();
  } else if (conflict?.kind === 'remote-deletion') {
    controller.discardThisConflictedTab();
  }
};
const handleKeepLocalConflict = (): void => {
  if (controller.localDraftConflict.value?.kind === 'created-elsewhere') {
    controller.keepConflictAsNewDraft();
  } else {
    controller.keepThisConflictDraft();
  }
};
const isDetailsOpen = computed(() => controller.detailsOpen.value);
const deckTitle = computed(() => {
  const name = controller.deck.form.name.trim();
  if (name) {
    return name;
  }
  return controller.deckId.value ? 'Untitled deck' : 'New deck';
});
const deckEditorSubtitle = computed(() => {
  if (!controller.deck.selectedHero.value) {
    return 'Choose a hero and add cards in any order.';
  }
  return `Build a mainboard with at least ${mainboardMinCards.value} cards, including ${manaMinCards.value} Mana cards.`;
});
</script>

<style scoped>
.deck-builder-status-bar {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--color-surface-strong);
}

.deck-builder-status-bar::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 1px;
  content: '';
  background: var(--color-border);
}

.deck-builder-loading-panel {
  min-height: 20rem;
}

.deck-builder-loading-line {
  position: relative;
  overflow: hidden;
  border-radius: 0.35rem;
  background: var(--color-surface-muted);
}

.deck-builder-loading-line::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(
    90deg,
    transparent 0%,
    color-mix(in srgb, var(--color-surface-strong) 58%, transparent) 48%,
    transparent 100%
  );
  animation: deck-builder-loading-sheen 1.6s ease-in-out infinite;
  transform: translateX(-100%);
}

@keyframes deck-builder-loading-sheen {
  to {
    transform: translateX(100%);
  }
}
</style>
