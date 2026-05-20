<template>
  <section class="space-y-5 xl:h-[calc(100vh-13rem)]">
    <div class="page-card space-y-4">
      <button
        class="btn-secondary inline-flex items-center gap-2"
        type="button"
        @click="goBack"
      >
        <ArrowLeft class="h-4 w-4" />
        <span>Back to Gallery</span>
      </button>

      <div
        v-if="card"
        class="flex w-full min-w-0 flex-col gap-3 lg:flex-row lg:items-start lg:justify-between lg:gap-6"
      >
        <div class="min-w-0">
          <h2 class="theme-section-title text-xl font-semibold">
            {{ card.name }}
          </h2>
          <p class="theme-section-muted text-xs">
            {{ versions.length }} versions
          </p>
          <div
            v-if="card.card_groups.length > 0"
            class="mt-3 flex flex-wrap gap-2"
          >
            <RouterLink
              v-for="group in card.card_groups"
              :key="group.id"
              :to="`/card-groups/${group.id}`"
              class="btn-secondary rounded-full px-3 py-1 text-xs font-medium"
            >
              <span>{{ group.name }}</span>
              <span class="theme-kicker">{{ group.member_count }} cards</span>
            </RouterLink>
          </div>
        </div>

        <div
          v-if="hasGalleryContext"
          class="flex flex-wrap items-center gap-2 lg:justify-end"
        >
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
          <span class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
            {{ positionLabel }}
          </span>
        </div>
      </div>
    </div>

    <div
      v-if="selectedVersion"
      class="grid items-start gap-5 xl:h-full xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]"
    >
      <div class="space-y-4 xl:h-full xl:overflow-y-auto xl:pr-2">
        <div>
          <CardVersionPreviewPane
            :version="selectedVersion"
            :symbol-by-key="symbolByKey"
            :to-absolute-api-url="toAbsoluteApiUrl"
            :format-date="formatDate"
          />
        </div>
        <CardVersionSelectorGrid
          :versions="versions"
          :selected-version-id="selectedVersionId"
          :to-absolute-api-url="toAbsoluteApiUrl"
          :format-date="formatDate"
          @select="selectVersion"
        />
      </div>
      <div class="xl:h-full xl:min-h-0">
        <CardVersionEditorPane
          :version="selectedVersion"
          :form="form"
          :is-busy="isBusy"
          :is-saving="isSaving"
          :is-queuing-reparse="isQueuingReparse"
          :save-message="saveMessage"
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
          @save="saveEdits"
          @restore-field="restoreField"
          @unlock-field="unlockField"
          @restore-group="restoreMetadataGroup"
          @unlock-group="unlockMetadataGroup"
          @reset-whole-card="resetWholeCardToAuto"
          @queue-reparse="queueLatestCardReparse"
          @toggle-group="toggleMetadataSelection"
          @update-group-search="setMetadataSearch"
          @update-field="updateField"
        />
      </div>
    </div>

    <div
      v-else
      class="page-card theme-section-muted text-sm"
    >
      No versions found.
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-vue-next';
import CardVersionEditorPane from '@/modules/card-detail/components/CardVersionEditorPane.vue';
import CardVersionPreviewPane from '@/modules/card-detail/components/CardVersionPreviewPane.vue';
import CardVersionSelectorGrid from '@/modules/card-detail/components/CardVersionSelectorGrid.vue';
import { useCardDetailState } from '@/modules/card-detail/composables/useCardDetailState';
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
  isSaving,
  isQueuingReparse,
  saveMessage,
  form,
  selectedVersion,
  isBusy,
  goBack,
  goToPreviousCard,
  goToNextCard,
  loadCard,
  selectVersion,
  saveEdits,
  restoreField,
  unlockField,
  restoreMetadataGroup,
  unlockMetadataGroup,
  resetWholeCardToAuto,
  queueLatestCardReparse,
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
  toAbsoluteApiUrl,
  formatDate,
} = useCardDetailState();

const updateField = (fieldName: ScalarFieldName, value: string): void => {
  form[fieldName] = value;
};

onMounted(loadCard);
</script>
