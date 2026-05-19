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
          <span class="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
            {{ positionLabel }}
          </span>
        </div>
      </div>

      <div v-if="group">
        <h2 class="text-2xl font-semibold text-slate-900">
          {{ group.name }}
        </h2>
        <p class="text-sm text-slate-500">
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
            <span class="text-sm font-semibold text-slate-900">
              {{ member.card.name }}
            </span>
            <span
              v-if="member.is_anchor"
              class="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-sky-700"
            >
              Anchor
            </span>
          </div>
          <RouterLink
            :to="`/cards/${member.card.id}`"
            class="text-sm font-medium text-sky-700 hover:text-sky-800"
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
import { onMounted, ref, watch } from 'vue';
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-vue-next';
import { useRoute, useRouter } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import CardVersionPreviewPane from '@/modules/card-detail/components/CardVersionPreviewPane.vue';
import { buildGalleryLocation, useGalleryCardNavigation } from '@/modules/card-search/galleryNavigation';
import type { CardFiltersResponse, CardGroupDetail, SymbolLookupMap } from '@/modules/card-detail/types';

const route = useRoute();
const router = useRouter();
const group = ref<CardGroupDetail | null>(null);
const symbolByKey = ref<SymbolLookupMap>({});
const galleryNavigation = useGalleryCardNavigation(route, router, 'detail');

const loadGroup = async (): Promise<void> => {
  const groupId = String(route.params.id);
  const [groupResponse, filtersResponse] = await Promise.all([
    api.get<CardGroupDetail>(`/card-groups/${groupId}`),
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

watch(() => route.params.id, loadGroup);
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
