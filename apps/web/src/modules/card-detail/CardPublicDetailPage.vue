<template>
  <section class="space-y-5 xl:h-[calc(100vh-8rem)]">
    <div class="page-card flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div class="space-y-3">
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          @click="goBack"
        >
          <ArrowLeft class="h-4 w-4" />
          <span>Back to Gallery</span>
        </button>

        <div v-if="card">
          <h2 class="text-2xl font-semibold text-slate-900">
            {{ card.name }}
          </h2>
          <p class="text-sm text-slate-500">
            Browse parsed versions and full card metadata.
          </p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          v-if="canEdit"
          class="btn-primary"
          type="button"
          @click="openEditor"
        >
          Edit Card
        </button>
      </div>
    </div>

    <div
      v-if="selectedVersion"
      class="grid items-start gap-5 xl:h-full xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)]"
    >
      <div class="space-y-4 xl:h-full xl:overflow-y-auto xl:pr-2">
        <CardVersionPreviewPane
          :version="selectedVersion"
          :symbol-by-key="symbolByKey"
          :to-absolute-api-url="toAbsoluteApiUrl"
          :format-date="formatDate"
          :show-editable-state="false"
        />
      </div>

      <div class="space-y-4 xl:h-full xl:overflow-y-auto xl:pr-2">
        <CardVersionSelectorGrid
          :versions="versions"
          :selected-version-id="selectedVersionId"
          :to-absolute-api-url="toAbsoluteApiUrl"
          :format-date="formatDate"
          title="Versions"
          description="Select a parsed version to inspect."
          @select="selectVersion"
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
import CardVersionPreviewPane from '@/modules/card-detail/components/CardVersionPreviewPane.vue';
import CardVersionSelectorGrid from '@/modules/card-detail/components/CardVersionSelectorGrid.vue';
import { useCardPublicDetailState } from '@/modules/card-detail/composables/useCardPublicDetailState';

const {
  card,
  versions,
  selectedVersionId,
  selectedVersion,
  symbolByKey,
  canEdit,
  loadCard,
  goBack,
  openEditor,
  selectVersion,
  toAbsoluteApiUrl,
  formatDate,
} = useCardPublicDetailState();

onMounted(loadCard);
</script>
