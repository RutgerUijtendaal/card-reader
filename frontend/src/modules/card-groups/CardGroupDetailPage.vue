<template>
  <section class="app-page-content flex flex-col gap-5">
    <AppPageHeader
      :icon="Layers3"
      :title="group?.name || 'Loading card group...'"
      :subtitle="group ? `${group.member_count} cards in this group` : 'Browse grouped card variants.'"
      :back-to="galleryBackLocation"
      back-label="Back to Gallery"
      title-tag="h2"
      title-class="text-2xl"
    />

    <nav
      v-if="hasGalleryContext"
      class="theme-divider flex flex-col gap-3 border-b pb-4 sm:flex-row sm:items-center sm:justify-between"
      aria-label="Card group result navigation"
    >
      <span class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
        {{ positionLabel }}
      </span>
      <div class="flex flex-wrap gap-2">
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :disabled="!previousCardId"
          @click="goToPreviousCard"
        >
          <ChevronLeft class="h-4 w-4" />
          <span>Previous</span>
        </button>
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          :disabled="!nextCardId && !hasMoreResults"
          @click="goToNextCard"
        >
          <span>{{ isLoadingMoreCards ? 'Loading Next...' : 'Next' }}</span>
          <ChevronRight class="h-4 w-4" />
        </button>
      </div>
    </nav>

    <div
      v-if="group"
      class="grid gap-6 2xl:grid-cols-2"
    >
      <div
        v-for="member in group.members"
        :key="`${group.id}-${member.card.id}`"
        class="space-y-3"
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
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { ChevronLeft, ChevronRight, Layers3 } from 'lucide-vue-next';
import { useRoute, useRouter } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import CardVersionOverviewPane from '@/components/cards/CardVersionOverviewPane.vue';
import {
  buildCardLifecycleApiParams,
  normalizeCardLifecycleFilterValue,
} from '@/composables/card-filters/cardLifecycle';
import { buildGalleryLocation, useGalleryCardNavigation } from '@/composables/card-gallery/galleryNavigation';
import type { CardFiltersResponse, CardGroupDetail, SymbolLookupMap } from '@/modules/card-detail/types';

const route = useRoute();
const router = useRouter();
const group = ref<CardGroupDetail | null>(null);
const symbolByKey = ref<SymbolLookupMap>({});
const galleryNavigation = useGalleryCardNavigation(route, router, 'detail');
const groupLifecycleStatus = computed(() => normalizeCardLifecycleFilterValue(route.query.lifecycle_status));
const groupRequestParams = computed(() => buildCardLifecycleApiParams(groupLifecycleStatus.value));
const galleryBackLocation = computed(() => buildGalleryLocation(route.query));

const loadGroup = async (): Promise<void> => {
  const groupId = String(route.params.id);
  const [groupResponse, filtersResponse] = await Promise.all([
    api.get<CardGroupDetail>(
      `/card-groups/${groupId}`,
      groupRequestParams.value ? { params: groupRequestParams.value } : undefined,
    ),
    api.get<CardFiltersResponse>('/cards/filters'),
  ]);
  group.value = groupResponse.data;
  symbolByKey.value = Object.fromEntries(
    (filtersResponse.data.symbols ?? []).map((row) => [row.key, row]),
  );
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
