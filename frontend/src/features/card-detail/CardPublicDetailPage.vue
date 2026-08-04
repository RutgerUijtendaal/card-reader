<template>
  <section class="app-page-content flex flex-col gap-5">
    <AppPageHeader
      :icon="Layers3"
      :title="card?.name || 'Loading card...'"
      subtitle="Browse parsed printings and full card metadata."
      :back-to="buildCardReturnLocation(route.query)"
      :back-label="backButtonLabel"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <AppHeaderAction
          v-if="canEdit"
          :icon="Pencil"
          label="Edit card"
          short-label="Edit"
          variant="primary"
          @click="openEditor"
        />
      </template>
    </AppPageHeader>

    <div
      v-if="isLoadingInitial"
      class="w-full"
    >
      <CardDetailLoadingSkeleton
        mode="public"
        :show-pager="hasGalleryContext"
      />
    </div>

    <div
      v-else-if="selectedVersion"
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
            :card-groups="card?.card_groups ?? []"
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

        <aside class="min-w-0 2xl:sticky 2xl:top-6 2xl:h-[calc(100vh-3rem)] 2xl:max-h-[calc(100vh-11rem)] 2xl:border-l 2xl:border-[var(--color-border)] 2xl:pl-6">
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
import { Layers3, Pencil } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import { toast } from 'vue-sonner';
import { api } from '@/shared/api/client';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import { useAuthStore } from '@/domain/session/store';
import { buildCardReturnLocation } from '@/domain/card-navigation/cardReturnState';
import { useReviewSummary } from '@/domain/review/composables/useReviewSummary';
import CardDeckReferencesPanel from '@/domain/card-deck-references/components/CardDeckReferencesPanel.vue';
import CardDetailLoadingSkeleton from '@/features/card-detail/components/CardDetailLoadingSkeleton.vue';
import CardDetailPager from '@/domain/cards/components/CardResultPager.vue';
import CardVersionParseFlagModal from '@/features/card-detail/components/CardVersionParseFlagModal.vue';
import CardVersionSelectorGrid from '@/features/card-detail/components/CardVersionSelectorGrid.vue';
import CardVersionOverviewPane from '@/domain/cards/components/CardVersionOverviewPane.vue';
import { useCardPublicDetailState } from '@/features/card-detail/composables/useCardPublicDetailState';
import type { ParseFlagCreatePayload } from '@/domain/review/types';

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
  isLoadingInitial,
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
