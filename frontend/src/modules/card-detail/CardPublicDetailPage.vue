<template>
  <section class="space-y-5 xl:h-[calc(100vh-13rem)]">
    <div class="page-card space-y-4 shadow-none">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          @click="goBack"
        >
          <ArrowLeft class="h-4 w-4" />
          <span>{{ backButtonLabel }}</span>
        </button>

        <button
          v-if="canEdit"
          class="btn-primary"
          type="button"
          @click="openEditor"
        >
          Edit Card
        </button>
      </div>

      <div
        v-if="card"
        class="flex w-full min-w-0 flex-col gap-3 lg:flex-row lg:items-start lg:justify-between lg:gap-6"
      >
        <div class="min-w-0">
          <h2 class="theme-section-title text-2xl font-semibold">
            {{ card.name }}
          </h2>
          <p class="theme-section-muted text-sm">
            Browse parsed versions and full card metadata.
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

      <div class="space-y-4 xl:h-full xl:overflow-y-auto">
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
      class="page-card theme-section-muted text-sm"
    >
      No versions found.
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-vue-next';
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
  backButtonLabel,
  hasGalleryContext,
  previousCardId,
  nextCardId,
  hasMoreResults,
  isLoadingMoreCards,
  positionLabel,
  loadCard,
  goBack,
  goToPreviousCard,
  goToNextCard,
  openEditor,
  selectVersion,
  toAbsoluteApiUrl,
  formatDate,
} = useCardPublicDetailState();

onMounted(loadCard);
</script>
