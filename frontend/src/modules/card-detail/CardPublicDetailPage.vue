<template>
  <section class="space-y-5 xl:h-[calc(100vh-13rem)]">
    <AppPageHeader
      :icon="Layers3"
      :title="card?.name || 'Loading card...'"
      subtitle="Browse parsed versions and full card metadata."
      :back-to="buildCardReturnLocation(route.query)"
      :back-label="backButtonLabel"
      title-tag="h2"
      title-class="text-2xl"
    >
      <template #actions>
        <button
          v-if="canEdit"
          class="btn-primary"
          type="button"
          @click="openEditor"
        >
          Edit Card
        </button>
      </template>

      <template
        v-if="card && card.card_groups.length > 0"
        #details
      >
        <div class="flex flex-wrap gap-2">
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
      </template>

      <template
        v-if="hasGalleryContext"
        #bottomRight
      >
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
    </AppPageHeader>

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
import { ChevronLeft, ChevronRight, Layers3 } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { buildCardReturnLocation } from '@/modules/card-detail/cardReturnState';
import CardVersionPreviewPane from '@/modules/card-detail/components/CardVersionPreviewPane.vue';
import CardVersionSelectorGrid from '@/modules/card-detail/components/CardVersionSelectorGrid.vue';
import { useCardPublicDetailState } from '@/modules/card-detail/composables/useCardPublicDetailState';

const route = useRoute();

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
  goToPreviousCard,
  goToNextCard,
  openEditor,
  selectVersion,
  toAbsoluteApiUrl,
  formatDate,
} = useCardPublicDetailState();

onMounted(loadCard);
</script>
