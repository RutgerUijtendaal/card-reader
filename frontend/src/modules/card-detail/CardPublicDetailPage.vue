<template>
  <section class="app-page-content flex flex-col gap-5">
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
    </AppPageHeader>

    <div
      v-if="selectedVersion"
      class="w-full"
    >
      <div class="grid items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(28rem,35vw)]">
        <div class="min-w-0 space-y-6">
          <CardDetailPager
            :visible="hasGalleryContext"
            :position-label="positionLabel"
            :previous-card-id="previousCardId"
            :next-card-id="nextCardId"
            :has-more-results="hasMoreResults"
            :is-loading-more-cards="isLoadingMoreCards"
            @previous="goToPreviousCard"
            @next="goToNextCard"
          />

          <CardVersionOverviewPane
            :version="selectedVersion"
            :symbol-by-key="symbolByKey"
            :to-absolute-api-url="toAbsoluteApiUrl"
            :can-flag="auth.authenticated"
            @flag-parse-issue="flagModalOpen = true"
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

    <CardVersionParseFlagModal
      :open="flagModalOpen"
      :version="selectedVersion"
      :submitting="flagSubmitting"
      :error-message="flagError"
      @close="closeFlagModal"
      @submit="submitParseFlag"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Layers3 } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildCardReturnLocation } from '@/composables/cards/cardReturnState';
import { useReviewSummary } from '@/composables/useReviewSummary';
import CardDeckReferencesPanel from '@/modules/card-detail/components/CardDeckReferencesPanel.vue';
import CardDetailPager from '@/modules/card-detail/components/CardDetailPager.vue';
import CardVersionParseFlagModal from '@/modules/card-detail/components/CardVersionParseFlagModal.vue';
import CardVersionSelectorGrid from '@/modules/card-detail/components/CardVersionSelectorGrid.vue';
import CardVersionOverviewPane from '@/components/cards/CardVersionOverviewPane.vue';
import { useCardPublicDetailState } from '@/modules/card-detail/composables/useCardPublicDetailState';
import type { ParseFlagCreatePayload } from '@/modules/card-detail/types';

const route = useRoute();
const auth = useAuthStore();
const flagModalOpen = ref(false);
const flagSubmitting = ref(false);
const flagError = ref('');
const { incrementOpenParseFlagItemCount } = useReviewSummary();

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

const closeFlagModal = (): void => {
  if (flagSubmitting.value) return;
  flagModalOpen.value = false;
  flagError.value = '';
};

const submitParseFlag = async (payload: ParseFlagCreatePayload): Promise<void> => {
  const version = selectedVersion.value;
  if (!version || payload.items.length === 0) return;
  flagSubmitting.value = true;
  flagError.value = '';
  try {
    await api.post(`/cards/${version.id}/versions/${version.version_id}/flags`, payload);
    if (auth.canAccessStaffRoutes) {
      incrementOpenParseFlagItemCount(payload.items.length);
    }
    flagModalOpen.value = false;
    toast.success('Parse issue submitted.');
  } catch (error) {
    flagError.value = extractErrorMessage(error, 'Failed to submit parse issue.');
  } finally {
    flagSubmitting.value = false;
  }
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  const maybeResponse = error as { response?: { data?: { detail?: unknown } } };
  const detail = maybeResponse.response?.data?.detail;
  return typeof detail === 'string' && detail.trim() ? detail : fallback;
};

onMounted(loadCard);
</script>
