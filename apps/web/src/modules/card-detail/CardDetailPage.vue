<template>
  <section class="space-y-5 xl:h-[calc(100vh-8rem)]">
    <div class="flex items-center justify-between gap-3">
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
        class="text-right"
      >
        <h2 class="text-xl font-semibold text-slate-900">
          {{ card.name }}
        </h2>
        <p class="text-xs text-slate-500">
          {{ versions.length }} versions
        </p>
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
          :save-message="saveMessage"
          :field-source="fieldSource"
          :metadata-source="metadataSource"
          :field-source-label="fieldSourceLabel"
          :metadata-source-label="metadataSourceLabel"
          :field-has-parsed-suggestion="fieldHasParsedSuggestion"
          :format-parsed-field-value="formatParsedFieldValue"
          :metadata-has-parsed-suggestion="metadataHasParsedSuggestion"
          :selected-ids="selectedIds"
          :parsed-metadata-labels="parsedMetadataLabels"
          :options-for-group="optionsForGroup"
          @save="saveEdits"
          @restore-field="restoreField"
          @unlock-field="unlockField"
          @restore-group="restoreMetadataGroup"
          @unlock-group="unlockMetadataGroup"
          @toggle-group="toggleMetadataSelection"
          @update-field="updateField"
        />
      </div>
    </div>

    <div
      v-else
      class="page-card text-sm text-slate-500"
    >
      No versions found.
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { ArrowLeft } from 'lucide-vue-next';
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
  isSaving,
  saveMessage,
  form,
  selectedVersion,
  isBusy,
  goBack,
  loadCard,
  selectVersion,
  saveEdits,
  restoreField,
  unlockField,
  restoreMetadataGroup,
  unlockMetadataGroup,
  fieldSource,
  metadataSource,
  fieldSourceLabel,
  metadataSourceLabel,
  fieldHasParsedSuggestion,
  formatParsedFieldValue,
  metadataHasParsedSuggestion,
  selectedIds,
  parsedMetadataLabels,
  optionsForGroup,
  toggleMetadataSelection,
  toAbsoluteApiUrl,
  formatDate,
} = useCardDetailState();

const updateField = (fieldName: ScalarFieldName, value: string): void => {
  form[fieldName] = value;
};

onMounted(loadCard);
</script>
