<template>
  <section class="flex flex-col gap-5">
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
      class="w-full"
    >
      <div class="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,35vw)]">
        <div class="min-w-0 space-y-6">
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

        <aside class="min-w-0 2xl:sticky 2xl:top-0 2xl:h-[calc(100vh-3rem)] 2xl:max-h-[calc(100vh-11rem)] 2xl:border-l 2xl:border-[var(--color-border)] 2xl:pl-6">
          <div class="space-y-5 2xl:app-scrollbar 2xl:h-full 2xl:overflow-y-auto 2xl:pr-1">
            <CardDeckReferencesPanel
              :deck-references="card?.deck_references ?? []"
              :current-user-id="auth.user?.id"
            />
          </div>
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
