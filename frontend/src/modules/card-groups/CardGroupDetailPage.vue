<template>
  <section class="space-y-5">
    <div class="page-card space-y-4 shadow-none">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <button
          class="btn-secondary inline-flex items-center gap-2"
          type="button"
          @click="goBack"
        >
          <ArrowLeft class="h-4 w-4" />
          <span>Back to Gallery</span>
        </button>

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
          <span class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
            {{ positionLabel }}
          </span>
        </div>
      </div>

      <div v-if="group">
        <h2 class="theme-section-title text-2xl font-semibold">
          {{ group.name }}
        </h2>
        <p class="theme-section-muted text-sm">
          {{ group.member_count }} cards in this group
        </p>
      </div>
    </div>

    <div
      v-if="group"
      class="grid gap-4 xl:grid-cols-2"
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

        <CardVersionPreviewPane
          :version="member.card"
          :symbol-by-key="symbolByKey"
          :to-absolute-api-url="toAbsoluteApiUrl"
          :format-date="formatDate"
          :show-editable-state="false"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-vue-next';
import { useRoute, useRouter } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import CardVersionPreviewPane from '@/modules/card-detail/components/CardVersionPreviewPane.vue';
import {
  DEFAULT_CARD_LIFECYCLE_FILTER,
  normalizeCardLifecycleFilterValue,
} from '@/modules/card-filters/cardFilterState';
import { buildGalleryLocation, useGalleryCardNavigation } from '@/modules/card-search/galleryNavigation';
import type { CardFiltersResponse, CardGroupDetail, SymbolLookupMap } from '@/modules/card-detail/types';

const route = useRoute();
const router = useRouter();
const group = ref<CardGroupDetail | null>(null);
const symbolByKey = ref<SymbolLookupMap>({});
const galleryNavigation = useGalleryCardNavigation(route, router, 'detail');
const groupLifecycleStatus = computed(() => normalizeCardLifecycleFilterValue(route.query.lifecycle_status));
const groupRequestParams = computed(() =>
  groupLifecycleStatus.value === DEFAULT_CARD_LIFECYCLE_FILTER
    ? undefined
    : { lifecycle_status: groupLifecycleStatus.value },
);

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

const goBack = (): void => {
  void router.push(buildGalleryLocation(route.query));
};

const formatDate = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
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
