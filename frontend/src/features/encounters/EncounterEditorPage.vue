<template>
  <section
    class="flex flex-col gap-6"
    :aria-busy="publication.isCreating.value"
  >
    <AppPageHeader
      :icon="APP_SECTION_ICONS.encounters"
      :title="editor.id ? 'Edit Encounter' : 'Build Encounter'"
      :subtitle="subtitle"
      :back-to="publication.isCreating.value ? null : '/my/encounters'"
      back-label="My Encounters"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #center>
        <nav
          class="deck-editor-section-tabs theme-tablist max-w-xl flex-nowrap justify-center"
          aria-label="Encounter editor sections"
        >
          <AppHeaderAction
            v-for="section in sections"
            :key="section.value"
            :icon="section.icon"
            :label="`Open encounter ${section.value}`"
            :short-label="section.label"
            variant="tab"
            :active="mode === section.value"
            :disabled="locked"
            @click="mode = section.value"
          />
        </nav>
      </template>
      <template #actions>
        <div
          class="deck-editor-header-divider theme-divider hidden h-6 border-l lg:block"
          aria-hidden="true"
        />
        <AppHeaderAction
          v-if="!editor.readOnly.value"
          :icon="busy ? LoaderCircle : editor.id ? Save : APP_SECTION_ICONS.encounters"
          :label="saveLabel"
          :short-label="saveLabel"
          variant="primary"
          :icon-class="busy ? 'animate-spin' : ''"
          :disabled="locked && !publication.hasTerminalNavigationRetry.value"
          @click="editor.save()"
        />
      </template>
    </AppPageHeader>
    <div
      v-if="editor.readOnly.value"
      class="app-page-content space-y-3"
      role="status"
    >
      <p>
        This Encounter is read only. Official Encounters can only be changed by staff. Your unsaved
        changes remain in this editor.
      </p>
      <RouterLink
        class="btn-secondary"
        :to="`/encounters/${editor.id}`"
      >
        View saved Encounter
      </RouterLink>
    </div>
    <div
      v-if="error || serverConflict || publication.isCreationUnknown.value"
      class="px-5 space-y-3"
    >
      <p
        v-if="error"
        class="theme-error-text"
        role="alert"
      >
        {{ error }}
      </p>
      <div
        v-if="serverConflict"
        class="space-y-2"
      >
        <p>
          Your changes are still in this editor. Reloading replaces them with the saved Encounter.
        </p>
        <button
          class="btn-secondary"
          @click="confirmReload"
        >
          Reload saved version
        </button>
      </div>
      <div
        v-if="publication.isCreationUnknown.value"
        class="space-y-2"
      >
        <p>Creation could not be confirmed. Retry safely uses the same request.</p>
        <button
          class="btn-primary"
          :disabled="publication.isReconciling.value"
          @click="publication.retry()"
        >
          Retry creation
        </button>
      </div>
    </div>
    <BuilderDetailsLayout v-if="mode === 'details'">
      <template #aside>
        <EncounterSelectionPanel
          :editor="editor"
          side="left"
        />
      </template>
      <template #status>
        <BuilderStatusBar aria-label="Encounter save status">
          <BuilderSaveStatus
            v-model:autosync="autosync"
            :busy="busy"
            :dirty="dirty"
            :label="editor.changeStatus.value"
            :saved="!!editor.id"
            :can-autosync="!!editor.id && !locked"
          />
        </BuilderStatusBar>
      </template>
      <EncounterDetailsForm :editor="editor" />
    </BuilderDetailsLayout>
    <BuilderWorkspaceLayout v-else>
      <template #aside>
        <CardBuilderFiltersPanel
          :filters="browser.filters"
          :total-count="browser.gallery.totalCount.value"
          :title="mode === 'boss' ? 'Boss Gallery' : 'Card Gallery'"
          :description="
            mode === 'boss' ? 'Browse boss cards and groups.' : 'Search and filter cards.'
          "
          :search-placeholder="mode === 'boss' ? 'Search bosses...' : 'Search cards...'"
          :show-current-only="mode === 'cards'"
          current-only-label="Current Encounter Only"
          :visible-sections="visibleFilters"
          :default-open-sections="['factions']"
        />
      </template>
      <template #status>
        <BuilderStatusBar aria-label="Encounter builder status">
          <BuilderSaveStatus
            v-model:autosync="autosync"
            :busy="busy"
            :dirty="dirty"
            :label="editor.changeStatus.value"
            :saved="!!editor.id"
            :can-autosync="!!editor.id && !locked"
          />
          <div class="flex flex-wrap items-center gap-x-5 gap-y-2">
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Cards</span><span class="theme-section-title text-base font-semibold">{{ total }}</span>
            </div>
            <div class="theme-divider hidden h-4 border-l lg:block" />
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Unique</span><span class="theme-section-title text-base font-semibold">{{
                form.entries.length
              }}</span>
            </div>
            <InfoTooltip
              v-if="issues.length"
              :text="issues.join(' ')"
              placement="bottom"
              :allow-flip="false"
            >
              <span
                class="theme-pill theme-pill-danger inline-flex items-center gap-1.5 px-2 py-1 text-xs font-semibold"
              ><TriangleAlert class="h-3.5 w-3.5" />{{ issues.length }}</span>
            </InfoTooltip>
            <div class="flex items-center gap-2">
              <span class="theme-kicker text-[11px] font-semibold uppercase tracking-wide">Status</span><span class="theme-section-title text-sm font-semibold">{{
                issues.length ? 'Incomplete' : dirty ? 'Pending validation' : 'Valid'
              }}</span>
            </div>
          </div>
        </BuilderStatusBar>
      </template>
      <div
        v-if="browser.error.value"
        class="theme-error-text p-4"
        role="alert"
      >
        {{ browser.error.value }}
        <button
          class="btn-secondary"
          @click="browser.reload()"
        >
          Retry
        </button>
      </div>
      <CardBuilderGallery
        v-else
        collection-label="Encounter"
        :gallery="browser.gallery"
        :loading="loading"
        :hover-mode="browser.filters.hoverMode.value"
        :selection-mode="mode === 'boss'"
        :is-selected="isSelected"
        :action-label="() => (mode === 'boss' ? 'Select boss' : 'Add card to Encounter')"
        :action-disabled="() => locked"
        :remove-disabled="(id) => locked || quantity(id) === 0"
        :quantity="quantity"
        :activate="activate"
        :remove="remove"
        :empty-message="
          mode === 'boss'
            ? 'No boss cards found for the current search.'
            : 'No cards found for the current filters.'
        "
      />
      <template #endAside>
        <EncounterSelectionPanel
          v-if="mode === 'boss'"
          :editor="editor"
        />
        <EncounterSummaryPanel
          v-else
          :editor="editor"
          :hover-mode="browser.filters.hoverMode.value"
        />
      </template>
    </BuilderWorkspaceLayout>
    <BuilderDraftRecoveryModal
      :open="!!draft.pendingRecovery.value && !draft.conflict.value"
      resource-label="Encounter"
      :saved-at="draft.pendingRecovery.value?.savedAt"
      :busy="editor.recoveryBusy.value"
      :discard-disabled="!!draft.pendingRecovery.value?.pendingCreateAttempt"
      @resume="editor.recover(draft.pendingRecovery.value!)"
      @discard="draft.discardRecovery()"
    />
    <BuilderDraftConflictModal
      :open="
        !!draft.conflict.value &&
          !publication.isCreating.value &&
          !publication.isCreationUnknown.value &&
          !publication.hasTerminalNavigationRetry.value &&
          !editor.recoveryBusy.value
      "
      resource-label="Encounter"
      :kind="draft.conflict.value?.kind"
      :busy="busy || editor.recoveryBusy.value"
      @use-stored="useStoredDraft"
      @keep-local="draft.overwriteConflict(true)"
    />
  </section>
</template>
<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { computed } from 'vue';
import { Crown, FileText, LayoutGrid, LoaderCircle, Save, TriangleAlert } from 'lucide-vue-next';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import BuilderDetailsLayout from '@/shared/components/builders/BuilderDetailsLayout.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import BuilderDraftRecoveryModal from '@/shared/components/builders/BuilderDraftRecoveryModal.vue';
import BuilderDraftConflictModal from '@/shared/components/builders/BuilderDraftConflictModal.vue';
import BuilderWorkspaceLayout from '@/shared/components/builders/BuilderWorkspaceLayout.vue';
import BuilderSaveStatus from '@/shared/components/builders/BuilderSaveStatus.vue';
import BuilderStatusBar from '@/shared/components/builders/BuilderStatusBar.vue';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import CardBuilderFiltersPanel from '@/domain/cards/components/CardBuilderFiltersPanel.vue';
import CardBuilderGallery from '@/domain/cards/components/CardBuilderGallery.vue';
import { emptyEncounter } from '@/domain/encounters/types';
import type { GalleryItem } from '@/domain/cards/types';
import type { CardFilterSectionKey } from '@/domain/cards/utils/filters/cardFilterSectionsState';
import EncounterDetailsForm from './components/EncounterDetailsForm.vue';
import EncounterSelectionPanel from './components/EncounterSelectionPanel.vue';
import EncounterSummaryPanel from './components/EncounterSummaryPanel.vue';
import { useEncounterEditor } from './composables/useEncounterEditor';
import { useEncounterBrowser } from './composables/useEncounterBrowser';
const editor = useEncounterEditor();
const {
  form,
  mode,
  loading,
  saving,
  error,
  locked,
  dirty,
  total,
  issues,
  draft,
  publication,
  serverConflict,
  autosync,
} = editor;
const browser = useEncounterBrowser({
  mode,
  bossFactions: editor.factions,
  cardIds: computed(() =>
    [...form.entries, ...form.sideboards.flatMap((board) => board.entries)].map(
      (entry) => entry.card_id,
    ),
  ),
});
const sections = [
  { value: 'boss', label: 'Boss', icon: Crown },
  { value: 'details', label: 'Details', icon: FileText },
  { value: 'cards', label: 'Cards', icon: LayoutGrid },
] as const;
const visibleFilters: CardFilterSectionKey[] = ['factions', 'types', 'keywords', 'tags', 'generic'];
const busy = computed(
  () => saving.value || publication.isCreating.value || publication.isReconciling.value,
);
const saveLabel = computed(() =>
  publication.hasTerminalNavigationRetry.value
    ? 'Continue'
    : busy.value
      ? 'Saving'
      : editor.id
        ? 'Save'
        : 'Create',
);
const subtitle = computed(() =>
  mode.value === 'boss'
    ? 'Choose the boss for this Encounter.'
    : mode.value === 'details'
      ? 'Edit the information people use to understand and discover this Encounter.'
      : `Build an Evil deck with at least ${editor.minimum.value} cards, excluding the boss.`,
);
const quantity = (id: string) =>
  editor.boards.activeBoardEntries.value.find((entry) => entry.card_id === id)?.quantity ?? 0;
const remove = (id: string) => editor.quantity(id, quantity(id) - 1);
const activate = (card: GalleryItem) => {
  if (mode.value === 'boss') void editor.selectBoss(card);
  else editor.add(card);
};
const isSelected = (card: GalleryItem) =>
  mode.value === 'boss' &&
  (card.result_type === 'card_group'
    ? form.boss_group_id === card.group_id
    : !form.boss_group_id && form.boss_card_id === card.id);
const confirmReload = () => {
  if (window.confirm('Replace your local edits with the saved Encounter?')) void editor.reload();
};
const useStoredDraft = () => {
  if (draft.conflict.value?.kind === 'active-draft') void editor.loadConflict();
  else if (draft.conflict.value?.kind === 'created-elsewhere') void editor.openCreated();
  else if (draft.discardThisTab()) {
    Object.assign(form, emptyEncounter());
    editor.cards.value = {};
  }
};
</script>
