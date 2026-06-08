<template>
  <section class="flex flex-col gap-6">
    <AppPageHeader
      :icon="Hammer"
      :title="controller.deckId.value ? 'Edit Deck' : 'Build Deck'"
      :subtitle="deckEditorSubtitle"
      :back-to="controller.backLink.value"
      :back-label="controller.backLabel.value"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <button
          v-if="!controller.deck.isSetupStep.value"
          class="btn-primary"
          type="button"
          :disabled="controller.manualSaving.value"
          @click="() => controller.saveDeck()"
        >
          {{ controller.manualSaving.value ? 'Saving...' : controller.deckId.value ? 'Save Deck' : 'Create Deck' }}
        </button>
      </template>
    </AppPageHeader>

    <div
      v-if="controller.loading.value"
      class="page-card theme-section-muted flex-1 text-sm"
    >
      Loading deck...
    </div>

    <template v-else>
      <AppPageLayout
        columns="three"
        root-class="deck-builder-layout"
        main-class="deck-builder-main-column"
      >
        <template #aside>
          <DeckBuilderFiltersPanel :controller="controller" />
        </template>
        <div class="flex min-w-0 flex-col gap-4">
          <section
            v-if="!controller.deck.isSetupStep.value"
            class="deck-builder-status-bar mx-px flex flex-col gap-4 px-4 py-3 lg:flex-row lg:items-center lg:justify-between"
            aria-label="Deck builder status"
          >
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
              <div class="flex items-center gap-2">
                <component
                  :is="deckChangeStatusIcon"
                  class="h-4 w-4 shrink-0"
                  :class="{ 'animate-spin': controller.saving.value }"
                />
                <span class="theme-section-title text-sm font-semibold">{{ controller.changeStatusLabel.value }}</span>
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
                <span>Autosync</span>
              </label>
            </div>

            <div class="flex flex-wrap items-center justify-start gap-x-5 gap-y-2 lg:justify-end">
              <div class="flex items-center gap-2">
                <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Total</span>
                <span class="theme-section-title text-base font-semibold">{{ controller.deck.overallTotalCards.value }}</span>
              </div>
              <div class="theme-divider hidden h-4 border-l lg:block" />
              <div class="flex items-center gap-2">
                <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Main</span>
                <span class="theme-section-title text-base font-semibold">
                  {{ controller.deck.totalMainboardCards.value }}<template v-if="controller.deck.totalMainboardCards.value >= mainboardMaxCards"> / {{ mainboardMaxCards }}</template>
                </span>
              </div>
              <div class="theme-divider hidden h-4 border-l lg:block" />
              <div class="flex items-center gap-2">
                <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Mana</span>
                <span class="theme-section-title text-base font-semibold">{{ controller.deck.totalMainboardManaTypeCards.value }}</span>
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
                <span class="theme-section-title text-base font-semibold">{{ controller.deck.overallUniqueCards.value }}</span>
              </div>
              <div class="theme-divider hidden h-4 border-l lg:block" />
              <div class="flex items-center gap-2">
                <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Status</span>
                <span
                  class="text-base font-semibold"
                  :class="controller.deck.isDeckValid.value ? 'text-emerald-300' : 'theme-section-title'"
                >
                  {{ controller.deck.deckStatusLabel.value }}
                </span>
              </div>
            </div>
          </section>

          <DeckBuilderGallery :controller="controller" />
        </div>
        <template #endAside>
          <DeckBuilderSummaryPanel :controller="controller" />
        </template>
      </AppPageLayout>
    </template>

    <ConfirmModal
      :open="controller.discardChangesModalOpen.value"
      title="Discard deck changes?"
      message="You have unsaved deck changes. Leaving this page will discard them."
      confirm-label="Discard Changes"
      cancel-label="Stay Here"
      @confirm="controller.confirmDiscardChanges"
      @cancel="controller.cancelDiscardChanges"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CircleCheckBig, CircleX, Cloud, CloudUpload, Hammer, LoaderCircle, TriangleAlert } from 'lucide-vue-next';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import InfoTooltip from '@/components/InfoTooltip.vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import DeckBuilderFiltersPanel from '@/modules/decks/components/DeckBuilderFiltersPanel.vue';
import DeckBuilderGallery from '@/modules/decks/components/DeckBuilderGallery.vue';
import DeckBuilderSummaryPanel from '@/modules/decks/components/DeckBuilderSummaryPanel.vue';
import { useDeckEditor } from '@/modules/decks/composables/useDeckEditor';
import { useFloatingPopover } from '@/composables/useFloatingPopover';

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
const mainboardMinCards = computed(() => controller.deckBuildingRules.value.mainboard_card_count.min ?? 0);
const mainboardMaxCards = computed(() => controller.deckBuildingRules.value.mainboard_card_count.max ?? 0);
const manaMinCards = computed(() => controller.deckBuildingRules.value.mana_type_count.min ?? 0);
const hardIssueMessages = computed(() => controller.deck.validationMessages.value);
const deckChangeStatusIcon = computed(() => {
  if (controller.saving.value) {
    return LoaderCircle;
  }
  if (controller.hasUnsavedChanges.value) {
    return CloudUpload;
  }
  return Cloud;
});
const deckEditorSubtitle = computed(() =>
  controller.deck.isSetupStep.value
    ? 'Select a hero and enter the deck details to continue.'
    : `Build a mainboard with at least ${mainboardMinCards.value} cards, including ${manaMinCards.value} Mana cards.`,
);
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
</style>
