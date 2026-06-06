<template>
  <section class="flex h-full min-h-0 flex-col gap-5 overflow-hidden">
    <AppPageHeader
      :icon="SquarePen"
      :title="card?.name || 'Loading card...'"
      subtitle="Review parsed versions and update the latest editable card data."
      :back-to="buildCardReturnLocation(route.query)"
      :back-label="backButtonLabel"
      title-tag="h2"
      title-class="text-xl"
    >
      <template
        v-if="cardIsDeprecated(card) || (card && card.card_groups.length > 0)"
        #titleMeta
      >
        <span
          v-if="cardIsDeprecated(card)"
          class="theme-pill theme-pill-warning inline-flex shrink-0 px-3 py-1 text-xs font-semibold uppercase tracking-wide"
        >
          Deprecated
        </span>
        <RouterLink
          v-for="group in card?.card_groups ?? []"
          :key="group.id"
          :to="`/card-groups/${group.id}`"
          class="btn-secondary inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
        >
          <span>{{ group.name }}</span>
          <span class="theme-kicker">{{ group.member_count }} cards</span>
        </RouterLink>
      </template>

      <template #bottomLeft>
        <template v-if="card">
          <button
            class="btn-secondary inline-flex items-center gap-2"
            type="button"
            @click="openCardMerge"
          >
            <GitMerge class="h-4 w-4" />
            <span>Merge/Rename</span>
          </button>
        </template>
      </template>

      <template #bottomRight>
        <template v-if="hasGalleryContext">
          <span class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
            {{ positionLabel }}
          </span>
          <button
            class="btn-secondary inline-flex items-center gap-2"
            type="button"
            :disabled="!previousCardId"
            @click="goToPreviousCard"
          >
            <ChevronLeft class="h-4 w-4" />
            <span>Previous Card</span>
          </button>
          <button
            class="btn-secondary inline-flex items-center gap-2"
            type="button"
            :disabled="!nextCardId && !hasMoreResults"
            @click="goToNextCard"
          >
            <span>{{ isLoadingMoreCards ? 'Loading Next...' : 'Next Card' }}</span>
            <ChevronRight class="h-4 w-4" />
          </button>
        </template>
      </template>
    </AppPageHeader>

    <div
      v-if="selectedVersion"
      class="app-scrollbar min-h-0 w-full flex-1 overflow-y-auto pr-1 xl:overflow-hidden xl:pr-0"
    >
      <div class="grid min-h-full items-start gap-6 xl:h-full xl:min-h-0 xl:grid-cols-[minmax(0,1fr)_minmax(30rem,40vw)] xl:items-stretch xl:overflow-hidden">
        <div class="app-scrollbar min-w-0 space-y-6 xl:min-h-0 xl:overflow-y-auto xl:pr-1">
          <CardVersionOverviewPane
            :version="selectedVersion"
            :symbol-by-key="symbolByKey"
            :to-absolute-api-url="toAbsoluteApiUrl"
          />

          <CardVersionSelectorGrid
            :versions="versions"
            :selected-version-id="selectedVersionId"
            :to-absolute-api-url="toAbsoluteApiUrl"
            :format-date="formatDate"
            class="border-t border-[var(--color-border)] pt-6"
            surface="plain"
            title="Printings"
            description="Select a printing to inspect or edit."
            allow-promote
            :promoting-version-id="promotingVersionId"
            @select="selectVersion"
            @promote="promoteVersion"
          />
        </div>

        <aside class="min-w-0 xl:h-full xl:min-h-0 xl:border-l xl:border-[var(--color-border)] xl:pl-6">
          <CardVersionEditorPane
            :version="selectedVersion"
            :form="form"
            :reparse-templates="reparseTemplates"
            :reparse-template-id="reparseTemplateId"
            :is-busy="isBusy"
            :is-saving="isSaving"
            :is-queuing-reparse="isQueuingReparse"
            :save-message="saveMessage"
            :deck-building-config-example="deckBuildingConfigExample"
            :field-source="fieldSource"
            :metadata-source="metadataSource"
            :field-source-label="fieldSourceLabel"
            :metadata-source-label="metadataSourceLabel"
            :field-has-parsed-suggestion="fieldHasParsedSuggestion"
            :format-parsed-field-value="formatParsedFieldValue"
            :metadata-has-parsed-suggestion="metadataHasParsedSuggestion"
            :metadata-search="metadataSearch"
            :selected-ids="selectedIds"
            :parsed-metadata-labels="parsedMetadataLabels"
            :options-for-group="optionsForGroup"
            :rule-text-symbols="rulesTextSymbols"
            :additional-symbol-ids="form.additional_symbol_ids"
            :rule-text-unknown-symbol-keys="ruleTextUnknownSymbolKeys"
            :deprecated-status-disabled="cardIsGroupAnchor"
            :review-focus-property-key="reviewFocusPropertyKey"
            @save-card="saveCardEdits"
            @save-version="saveVersionEdits"
            @restore-field="restoreField"
            @unlock-field="unlockField"
            @restore-group="restoreMetadataGroup"
            @unlock-group="unlockMetadataGroup"
            @reset-whole-card="resetWholeCardToAuto"
            @queue-reparse="queueLatestCardReparse"
            @update-reparse-template="updateReparseTemplate"
            @toggle-group="toggleMetadataSelection"
            @toggle-additional-symbol="toggleAdditionalSymbol"
            @update-group-search="setMetadataSearch"
            @update-field="updateField"
            @update-hero="updateHero"
            @update-deck-building-config="updateDeckBuildingConfig"
            @update-lifecycle-status="updateLifecycleStatus"
          />
        </aside>
      </div>
    </div>

    <div
      v-else
      class="page-card theme-section-muted text-sm"
    >
      No printings found.
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { ChevronLeft, ChevronRight, GitMerge, SquarePen } from 'lucide-vue-next';
import { useRouter } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { buildAdminCardMergeSourceLocation } from '@/composables/admin/adminRouteState';
import { buildCardReturnLocation } from '@/composables/cards/cardReturnState';
import CardVersionEditorPane from '@/modules/card-detail/components/CardVersionEditorPane.vue';
import CardVersionOverviewPane from '@/components/cards/CardVersionOverviewPane.vue';
import CardVersionSelectorGrid from '@/modules/card-detail/components/CardVersionSelectorGrid.vue';
import { useCardDetailState } from '@/modules/card-detail/composables/useCardDetailState';
import {
  cardIsDeprecated,
  type CardLifecycleStatus,
} from '@/composables/card-filters/cardLifecycle';
import type { ScalarFieldName } from '@/modules/card-detail/types';

const {
  card,
  versions,
  selectedVersionId,
  symbolByKey,
  hasGalleryContext,
  previousCardId,
  nextCardId,
  hasMoreResults,
  isLoadingMoreCards,
  positionLabel,
  reparseTemplates,
  reparseTemplateId,
  isSaving,
  isQueuingReparse,
  promotingVersionId,
  saveMessage,
  deckBuildingConfigExample,
  form,
  selectedVersion,
  isBusy,
  ruleTextUnknownSymbolKeys,
  rulesTextSymbols,
  backButtonLabel,
  reviewFocusPropertyKey,
  route,
  goToPreviousCard,
  goToNextCard,
  loadCard,
  selectVersion,
  saveCardEdits,
  saveVersionEdits,
  restoreField,
  unlockField,
  restoreMetadataGroup,
  unlockMetadataGroup,
  resetWholeCardToAuto,
  queueLatestCardReparse,
  promoteVersion,
  fieldSource,
  metadataSource,
  fieldSourceLabel,
  metadataSourceLabel,
  fieldHasParsedSuggestion,
  formatParsedFieldValue,
  metadataHasParsedSuggestion,
  metadataSearch,
  selectedIds,
  parsedMetadataLabels,
  optionsForGroup,
  setMetadataSearch,
  toggleMetadataSelection,
  toggleAdditionalSymbol,
  toAbsoluteApiUrl,
  formatDate,
} = useCardDetailState();

const router = useRouter();
const cardIsGroupAnchor = computed(() => card.value?.card_groups.some((group) => group.is_anchor) ?? false);

const updateField = (fieldName: ScalarFieldName, value: string): void => {
  form[fieldName] = value;
};

const updateHero = (value: boolean): void => {
  form.is_hero = value;
};

const updateDeckBuildingConfig = (value: string): void => {
  form.deck_building_config = value;
};

const updateLifecycleStatus = (value: CardLifecycleStatus): void => {
  if (value === 'deprecated' && cardIsGroupAnchor.value) return;
  form.lifecycle_status = value;
};

const updateReparseTemplate = (value: string): void => {
  reparseTemplateId.value = value;
};

const openCardMerge = (): void => {
  if (!card.value) return;
  void router.push(buildAdminCardMergeSourceLocation(card.value.id, route.query));
};

onMounted(loadCard);
</script>
