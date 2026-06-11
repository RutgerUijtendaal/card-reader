<template>
  <section class="app-page-content flex flex-col gap-5">
    <AppPageHeader
      :icon="Layers3"
      :title="group?.name || 'Loading card group...'"
      :subtitle="group ? `${group.member_count} cards in this group` : 'Browse grouped card variants.'"
      :back-to="galleryBackLocation"
      back-label="Back to Gallery"
      title-tag="h2"
      title-class="text-xl"
    />

    <CardGroupDetailLoadingSkeleton
      v-if="isLoadingInitial"
      :show-pager="hasGalleryContext"
    />

    <div
      v-else-if="group"
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

          <div class="space-y-6">
            <section
              v-for="member in group.members"
              :key="`${group.id}-${member.card.id}`"
              class="space-y-4 border-t border-[var(--color-border)] pt-6 first:border-t-0 first:pt-0"
            >
              <div class="flex items-center justify-between gap-3 px-1">
                <div class="flex items-center gap-2">
                  <span class="theme-section-title text-sm font-semibold">
                    {{ member.card.name }}
                  </span>
                  <span
                    v-if="member.is_anchor"
                    class="theme-pill theme-pill-neutral px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
                  >
                    Anchor
                  </span>
                </div>
                <RouterLink
                  :to="`/cards/${member.card.id}`"
                  class="theme-link text-sm font-medium transition"
                >
                  Open card
                </RouterLink>
              </div>

              <CardVersionOverviewPane
                :version="member.card"
                :symbol-by-key="symbolByKey"
                :to-absolute-api-url="toAbsoluteApiUrl"
              />
            </section>
          </div>
        </div>

        <aside class="min-w-0 2xl:sticky 2xl:top-6 2xl:h-[calc(100vh-3rem)] 2xl:max-h-[calc(100vh-11rem)] 2xl:border-l 2xl:border-[var(--color-border)] 2xl:pl-6">
          <div class="space-y-5 2xl:app-scrollbar 2xl:h-full 2xl:overflow-y-auto 2xl:pr-1">
            <CardDeckReferencesPanel
              :deck-references="group.anchor_deck_references"
              :current-user-id="auth.user?.id"
              :source-card-id="group.anchor_card_id"
            />
          </div>
        </aside>
      </div>
    </div>

    <div
      v-else
      class="page-card theme-section-muted text-sm"
    >
      Card group not found.
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { Layers3 } from 'lucide-vue-next';
import { useRoute, useRouter } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import CardDeckReferencesPanel from '@/components/cards/CardDeckReferencesPanel.vue';
import CardDetailPager from '@/components/cards/CardResultPager.vue';
import CardVersionOverviewPane from '@/components/cards/CardVersionOverviewPane.vue';
import {
  buildCardLifecycleApiParams,
  normalizeCardLifecycleFilterValue,
} from '@/composables/card-filters/cardLifecycle';
import { buildGalleryLocation, useGalleryCardNavigation } from '@/composables/card-gallery/galleryNavigation';
import { useAuthStore } from '@/modules/auth/authStore';
import CardGroupDetailLoadingSkeleton from '@/modules/card-groups/components/CardGroupDetailLoadingSkeleton.vue';
import type { CardFiltersResponse, CardGroupDetail, SymbolLookupMap } from '@/modules/card-detail/types';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const group = ref<CardGroupDetail | null>(null);
const symbolByKey = ref<SymbolLookupMap>({});
const isLoadingInitial = ref(true);
const galleryNavigation = useGalleryCardNavigation(route, router, 'detail');
const groupLifecycleStatus = computed(() => normalizeCardLifecycleFilterValue(route.query.lifecycle_status));
const groupRequestParams = computed(() => buildCardLifecycleApiParams(groupLifecycleStatus.value));
const galleryBackLocation = computed(() => buildGalleryLocation(route.query));
let groupRequestId = 0;

const loadGroup = async (): Promise<void> => {
  const requestId = groupRequestId + 1;
  groupRequestId = requestId;
  isLoadingInitial.value = true;
  const groupId = String(route.params.id);
  try {
    const [groupResponse, filtersResponse] = await Promise.all([
      api.get<CardGroupDetail>(
        `/card-groups/${groupId}`,
        groupRequestParams.value ? { params: groupRequestParams.value } : undefined,
      ),
      api.get<CardFiltersResponse>('/cards/filters'),
    ]);
    if (requestId !== groupRequestId) return;
    group.value = groupResponse.data;
    symbolByKey.value = Object.fromEntries(
      (filtersResponse.data.symbols ?? []).map((row) => [row.key, row]),
    );
  } finally {
    if (requestId === groupRequestId) {
      isLoadingInitial.value = false;
    }
  }
};

watch(() => [route.params.id, route.query.lifecycle_status], loadGroup);
onMounted(loadGroup);

const {
  hasGalleryContext,
  previousCardId,
  nextCardId,
  hasMoreResults,
  isLoadingMoreCards,
  positionLabel,
  goToPreviousCard,
  goToNextCard,
} = galleryNavigation;
</script>
