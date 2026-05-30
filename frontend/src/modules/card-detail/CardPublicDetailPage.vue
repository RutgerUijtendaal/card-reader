<template>
  <section class="flex h-full min-h-0 flex-col gap-5 overflow-hidden">
    <AppPageHeader
      :icon="Layers3"
      :title="card?.name || 'Loading card...'"
      subtitle="Browse parsed printings and full card metadata."
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
            description="Select a printing to inspect."
            @select="selectVersion"
          />
        </div>

        <aside class="app-scrollbar min-w-0 space-y-5 xl:h-full xl:min-h-0 xl:overflow-y-auto xl:border-l xl:border-[var(--color-border)] xl:pl-6 xl:pr-1">
          <CardDeckReferencesPanel
            :deck-references="card?.deck_references ?? []"
            :current-user-id="auth.user?.id"
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
import { onMounted } from 'vue';
import { ChevronLeft, ChevronRight, Layers3 } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildCardReturnLocation } from '@/modules/card-detail/cardReturnState';
import CardDeckReferencesPanel from '@/modules/card-detail/components/CardDeckReferencesPanel.vue';
import CardVersionSelectorGrid from '@/modules/card-detail/components/CardVersionSelectorGrid.vue';
import CardVersionOverviewPane from '@/modules/card-detail/components/CardVersionOverviewPane.vue';
import { useCardPublicDetailState } from '@/modules/card-detail/composables/useCardPublicDetailState';

const route = useRoute();
const auth = useAuthStore();

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
