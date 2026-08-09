<template>
  <section
    class="flex flex-col gap-6"
    :inert="controller.isCreating.value"
    :aria-busy="controller.isCreating.value"
  >
    <AppPageHeader
      :icon="Hammer"
      :title="controller.deckId.value ? 'Edit Deck' : 'Build Deck'"
      :subtitle="deckEditorSubtitle"
      :back-to="controller.isCreating.value ? null : controller.backLink.value"
      :back-label="controller.backLabel.value"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <div
          v-if="!controller.isChangingHero.value"
          class="deck-editor-header-divider theme-divider hidden h-6 border-l lg:block"
          aria-hidden="true"
        />
        <div
          v-if="!controller.isChangingHero.value"
          class="flex items-center gap-2"
        >
          <AppHeaderAction
            v-if="!controller.isPublished.value && controller.hasLocalDraft.value"
            :icon="Trash2"
            label="Discard local draft"
            short-label="Discard"
            :disabled="controller.isCreating.value"
            @click="controller.requestDiscardLocalDraft()"
          />
          <AppHeaderAction
            :icon="deckSaveActionIcon"
            :label="deckSaveActionLabel"
            :short-label="deckSaveActionShortLabel"
            variant="primary"
            :icon-class="controller.manualSaving.value ? 'animate-spin' : ''"
            :disabled="controller.manualSaving.value"
            @click="() => controller.saveDeck()"
          />
        </div>
      </template>
      <template #center>
        <nav
          v-if="!controller.isChangingHero.value"
          class="deck-editor-section-tabs theme-tablist max-w-xl flex-nowrap justify-center"
          aria-label="Deck editor sections"
        >
          <AppHeaderAction
            v-if="!controller.isPublished.value"
            :icon="Crown"
            label="Open deck hero"
            short-label="Hero"
            variant="tab"
            :active="controller.editorMode.value === 'hero'"
            :disabled="controller.isCreating.value"
            @click="controller.openHero()"
          />
          <AppHeaderAction
            :icon="FileText"
            label="Open deck details"
            short-label="Details"
            variant="tab"
            :active="controller.editorMode.value === 'details'"
            :disabled="controller.isCreating.value"
            @click="controller.openDetails()"
          />
          <AppHeaderAction
            :icon="LayoutGrid"
            label="Open deck cards"
            short-label="Cards"
            variant="tab"
            :active="controller.editorMode.value === 'cards'"
            :disabled="controller.isCreating.value"
            @click="controller.openCards()"
          />
        </nav>
      </template>
    </AppPageHeader>

    <AppPageLayout
      v-if="controller.loading.value && controller.editorMode.value !== 'cards'"
      columns="sidebar"
      aria-label="Loading deck details"
    >
      <template #aside>
        <aside class="app-sticky-aside app-sticky-aside-left deck-builder-loading-panel">
          <div class="app-sticky-aside-scroll space-y-5">
            <div class="space-y-3">
              <div class="deck-builder-loading-line h-5 w-20" />
              <div class="deck-builder-loading-line h-4 w-full" />
            </div>
            <div class="deck-builder-loading-line mx-auto aspect-[63/88] w-full max-w-48 rounded-xl" />
            <div class="deck-builder-loading-line mx-auto h-5 w-32" />
            <div class="deck-builder-loading-line h-10 w-full" />
          </div>
        </aside>
      </template>

      <div
        class="mx-auto w-full max-w-4xl space-y-8"
        aria-hidden="true"
      >
        <div class="space-y-3">
          <div class="deck-builder-loading-line h-7 w-36" />
          <div class="deck-builder-loading-line h-4 w-80 max-w-full" />
        </div>
        <div class="space-y-5">
          <div class="deck-builder-loading-line h-11 w-full" />
          <div class="deck-builder-loading-line h-20 w-full" />
          <div class="deck-builder-loading-line h-64 w-full" />
        </div>
        <div class="space-y-3">
          <div class="deck-builder-loading-line h-6 w-32" />
          <div class="deck-builder-loading-line h-24 w-full" />
        </div>
      </div>
    </AppPageLayout>

    <AppPageLayout
      v-if="!controller.loading.value && controller.editorMode.value === 'hero'"
      columns="three"
      root-class="deck-builder-layout"
      main-class="deck-builder-main-column"
    >
      <template #aside>
        <DeckBuilderFiltersPanel :controller="controller" />
      </template>
      <div class="deck-builder-gallery-column flex min-w-0 flex-col">
        <div class="deck-builder-gallery-scroll app-scrollbar min-h-0 flex-1">
          <DeckBuilderGallery :controller="controller" />
        </div>
      </div>
      <template #endAside>
        <DeckHeroSelectionPanel :controller="controller" />
      </template>
    </AppPageLayout>

    <AppPageLayout
      v-if="!controller.loading.value && controller.editorMode.value === 'details'"
      columns="sidebar"
    >
      <template #aside>
        <DeckDetailsHeroPanel :controller="controller" />
      </template>
      <DeckDetailsForm :controller="controller" />
    </AppPageLayout>

    <AppPageLayout
      v-if="controller.editorMode.value === 'cards'"
      columns="three"
      root-class="deck-builder-layout"
      main-class="deck-builder-main-column"
    >
      <template #aside>
        <aside
          v-if="controller.loading.value"
          class="app-sticky-aside app-sticky-aside-left deck-builder-loading-panel"
        >
          <div class="app-sticky-aside-scroll space-y-6">
            <div class="space-y-3">
              <div class="deck-builder-loading-line h-4 w-28" />
              <div class="deck-builder-loading-line h-10 w-full" />
              <div class="deck-builder-loading-line h-10 w-5/6" />
            </div>
            <div class="space-y-3">
              <div class="deck-builder-loading-line h-4 w-20" />
              <div
                v-for="index in 5"
                :key="`loading-filter-${index}`"
                class="deck-builder-loading-line h-8 w-full"
              />
            </div>
          </div>
        </aside>
        <DeckBuilderFiltersPanel
          v-else
          :controller="controller"
        />
      </template>
      <div class="deck-builder-gallery-column flex min-w-0 flex-col gap-4">
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
        <section
          v-else
          class="deck-builder-status-bar mx-px flex shrink-0 flex-col gap-4 px-4 py-3 lg:flex-row lg:items-center lg:justify-between"
          aria-label="Deck builder status"
        >
          <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
            <div class="flex items-center gap-2">
              <component
                :is="deckChangeStatusIcon"
                class="h-4 w-4 shrink-0"
                :class="{ 'animate-spin': controller.saving.value }"
              />
              <span class="theme-section-title text-sm font-semibold">{{
                controller.changeStatusLabel.value
              }}</span>
            </div>
            <label
              class="theme-section-muted flex items-center gap-2 text-sm font-semibold"
              :class="{ 'opacity-60': !controller.canAutosync.value }"
            >
              <input
                v-model="controller.autosyncEnabled.value"
                class="h-4 w-4 rounded accent-emerald-400"
                type="checkbox"
                :disabled="!controller.canAutosync.value"
              >
              <span>{{ controller.isPublished.value ? 'Autosync' : 'Autosync after creation' }}</span>
            </label>
          </div>

          <div class="flex flex-wrap items-center justify-start gap-x-5 gap-y-2 lg:justify-end">
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Total</span>
              <span class="theme-section-title text-base font-semibold">{{
                controller.deck.overallTotalCards.value
              }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Main</span>
              <span class="theme-section-title text-base font-semibold">
                {{ controller.deck.totalMainboardCards.value
                }}<template v-if="controller.deck.totalMainboardCards.value >= mainboardMaxCards">
                  / {{ mainboardMaxCards }}</template>
              </span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Mana</span>
              <span class="theme-section-title text-base font-semibold">{{
                controller.deck.totalMainboardManaTypeCards.value
              }}</span>
              <InfoTooltip
                text="If at least 25% of your deck is Mana cards, you can mulligan anytime you draw a starting hand with 0 mana cards."
                placement="bottom"
                :allow-flip="false"
              >
                <CircleCheckBig
                  v-if="controller.deck.hasFreeMulliganManaRatio.value"
                  class="h-4 w-4 text-emerald-400"
                />
                <CircleX
                  v-else
                  class="h-4 w-4 text-rose-400"
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
                  class="theme-popover pointer-events-none z-50 w-72 p-3 text-sm shadow-lg"
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
                  class="theme-popover pointer-events-none z-50 w-72 p-3 text-sm shadow-lg"
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
              <span class="theme-section-title text-base font-semibold">{{
                controller.deck.overallUniqueCards.value
              }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Status</span>
              <span
                class="text-base font-semibold"
                :class="
                  controller.deck.isDeckValid.value ? 'text-emerald-300' : 'theme-section-title'
                "
              >
                {{ controller.deck.deckStatusLabel.value }}
              </span>
            </div>
          </div>
        </section>

        <div class="deck-builder-gallery-scroll app-scrollbar min-h-0 flex-1">
          <DeckBuilderGallery
            :controller="controller"
            :loading="controller.loading.value"
          />
        </div>
      </div>
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
    </AppPageLayout>

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
      @resume="controller.resumeLocalDraft"
      @discard="controller.discardPendingLocalDraft"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  CircleCheckBig,
  CircleX,
  Cloud,
  CloudUpload,
  Crown,
  FileText,
  Hammer,
  LayoutGrid,
  LoaderCircle,
  Save,
  Trash2,
  TriangleAlert,
} from 'lucide-vue-next';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';
import ConfirmModal from '@/shared/components/modals/ConfirmModal.vue';
import DeckBuilderFiltersPanel from '@/features/decks/components/DeckBuilderFiltersPanel.vue';
import DeckBuilderGallery from '@/features/decks/components/DeckBuilderGallery.vue';
import DeckBuilderSummaryPanel from '@/features/decks/components/DeckBuilderSummaryPanel.vue';
import DeckDetailsForm from '@/features/decks/components/DeckDetailsForm.vue';
import DeckDetailsHeroPanel from '@/features/decks/components/DeckDetailsHeroPanel.vue';
import DeckDraftRecoveryModal from '@/features/decks/components/DeckDraftRecoveryModal.vue';
import DeckHeroSelectionPanel from '@/features/decks/components/DeckHeroSelectionPanel.vue';
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
  if (controller.manualSaving.value) {
    return LoaderCircle;
  }
  return controller.isPublished.value ? Save : Hammer;
});
const deckSaveActionLabel = computed(() => {
  if (controller.manualSaving.value) {
    return controller.isPublished.value ? 'Saving deck' : 'Creating deck';
  }
  return controller.isPublished.value ? 'Save deck' : 'Create deck';
});
const deckSaveActionShortLabel = computed(() =>
  controller.isPublished.value ? 'Save' : 'Create',
);
const deckLeaveConfirmationMessage = computed(() => {
  if (controller.isPublished.value) {
    return 'You have unsaved deck changes. Leaving this page will discard them.';
  }
  if (controller.localDraftPersistenceFailed.value) {
    return 'This draft could not be saved in this browser. Leaving now will discard your current progress.';
  }
  return 'Your unpublished deck will remain saved in this browser so you can resume it later.';
});
const deckLeaveConfirmationLabel = computed(() => {
  if (controller.isPublished.value) {
    return 'Discard Changes';
  }
  return controller.localDraftPersistenceFailed.value ? 'Discard & Leave' : 'Leave Draft';
});
const deckChangeStatusIcon = computed(() => {
  if (controller.saving.value) {
    return LoaderCircle;
  }
  if (controller.hasUnsavedChanges.value) {
    return CloudUpload;
  }
  return Cloud;
});
const deckEditorSubtitle = computed(() => {
  if (controller.editorMode.value === 'hero') {
    return controller.isChangingHero.value
      ? 'Choose a replacement hero, then apply or cancel the change.'
      : 'Choose the hero that will shape this deck.';
  }
  if (controller.editorMode.value === 'details') {
    return 'Edit the information people use to understand and discover this deck.';
  }
  return `Build a mainboard with at least ${mainboardMinCards.value} cards, including ${manaMinCards.value} Mana cards.`;
});
</script>

<style scoped>
:deep(.deck-builder-layout) {
  padding-top: 0;
  padding-right: 0;
  padding-left: 0;
}

:deep(.deck-builder-main-column) {
  padding-top: 0;
  padding-right: 0;
  padding-left: 0;
}

@media (min-width: 1280px) {
  :deep(.deck-builder-layout) {
    height: calc(100dvh - var(--app-page-header-height, 0px));
    min-height: 0;
    overflow: hidden;
  }

  :deep(.deck-builder-main-column) {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .deck-builder-gallery-column {
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .deck-builder-gallery-scroll {
    overflow-y: auto;
    overscroll-behavior: contain;
  }
}

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
