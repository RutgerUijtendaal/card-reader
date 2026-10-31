<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="APP_SECTION_ICONS.encounters"
      :title="staff ? 'Manage Encounters' : mine ? 'My Encounters' : 'Encounters'"
      :subtitle="
        staff
          ? 'Manage all saved Encounters, including private and unfinished work.'
          : mine
            ? 'Your Encounters, including private and unfinished work.'
            : 'Browse public Encounters and discover your next fight.'
      "
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <AppHeaderAction
          v-if="auth.canAccessStaffRoutes && !staff"
          :icon="APP_SECTION_ICONS.encounters"
          label="Manage Encounters"
          short-label="Manage"
          :to="{ path: '/staff/encounters', query: filterQuery }"
        />
        <AppHeaderAction
          v-if="auth.authenticated"
          :icon="APP_SECTION_ICONS.encounters"
          label="Build Encounter"
          short-label="Build Encounter"
          variant="primary"
          to="/my/encounters/new"
        />
      </template>
    </AppPageHeader>
    <AppPageLayout>
      <template #aside>
        <GalleryFilterSidebar
          title="Encounter Filters"
          description="Search by name and assigned factions."
          :query="query"
          :on-update-query="(value) => (query = value)"
          search-placeholder="Search Encounters..."
          :total-count="count"
          :on-reset="reset"
        >
          <div
            v-if="auth.authenticated"
            class="theme-divider space-y-3 border-b pb-4"
          >
            <p class="theme-kicker text-xs font-semibold uppercase tracking-[0.16em]">
              Encounter Library
            </p>
            <div class="theme-tablist w-full">
              <RouterLink
                class="theme-tab flex-1"
                :class="!staff && !mine ? 'theme-tab-active' : ''"
                :to="{ path: '/encounters', query: filterQuery }"
              >
                Public
              </RouterLink>
              <RouterLink
                class="theme-tab flex-1"
                :class="mine ? 'theme-tab-active' : ''"
                :to="{ path: '/my/encounters', query: filterQuery }"
              >
                My Encounters
              </RouterLink>
            </div>
          </div>
          <div class="space-y-3">
            <h3 class="theme-section-title text-sm font-semibold">
              Official status
            </h3>
            <div class="flex flex-wrap gap-2">
              <ChoicePill
                v-for="option in officialOptions"
                :key="option.value"
                :selected="official === option.value"
                @click="official = option.value"
              >
                {{ option.label }}
              </ChoicePill>
            </div>
          </div>
          <div class="space-y-3">
            <h3 class="theme-section-title text-sm font-semibold">
              Factions
            </h3>
            <div class="flex flex-wrap gap-2">
              <ChoicePill
                v-for="option in CARD_FACTION_OPTIONS"
                :key="option.value"
                :selected="factions.includes(option.value)"
                @click="toggleFaction(option.value)"
              >
                {{ option.label }}
              </ChoicePill>
            </div>
          </div>
        </GalleryFilterSidebar>
      </template>
      <div
        v-if="loading"
        class="app-page-single-column grid gap-4"
        aria-label="Loading Encounters"
      >
        <CollectionLoadingSkeleton
          v-for="index in 10"
          :key="index"
        />
      </div>
      <div
        v-else-if="error"
        class="page-card theme-section-muted flex items-center justify-between gap-3 text-sm"
        role="alert"
      >
        <span>{{ error }}</span><button
          class="btn-secondary"
          type="button"
          @click="load()"
        >
          Retry
        </button>
      </div>
      <div
        v-else-if="!records.length"
        class="page-card theme-section-muted text-sm"
      >
        {{
          query || factions.length || official
            ? 'No Encounters match the current filters.'
            : staff || mine
              ? 'No saved Encounters yet.'
              : 'No public Encounters yet.'
        }}
      </div>
      <div
        v-else
        class="app-page-single-column grid gap-4"
      >
        <EncounterListCard
          v-for="item in records"
          :key="item.id"
          :encounter="item"
          :staff="staff"
          :mine="mine"
          :filter-query="filterQuery"
        />
        <div
          v-if="nextPage"
          ref="sentinel"
          class="flex justify-center py-4"
        >
          <div
            v-if="moreError"
            class="theme-error-text text-sm"
            role="alert"
          >
            {{ moreError }}
          </div>
          <button
            class="btn-secondary"
            type="button"
            :disabled="loadingMore"
            @click="load(true)"
          >
            {{
              loadingMore ? 'Loading...' : moreError ? 'Retry loading more' : 'Load more Encounters'
            }}
          </button>
        </div>
      </div>
    </AppPageLayout>
  </section>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { useIntersectionObserver } from '@vueuse/core';
import { CARD_FACTION_OPTIONS } from '@/domain/cards/cardFactions';
import { useAuthStore } from '@/domain/session/store';
import GalleryFilterSidebar from '@/domain/cards/components/filters/GalleryFilterSidebar.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import CollectionLoadingSkeleton from '@/shared/components/CollectionLoadingSkeleton.vue';
import ChoicePill from '@/shared/components/ChoicePill.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import EncounterListCard from './components/EncounterListCard.vue';
import { useEncounterList } from './composables/useEncounterList';
const auth = useAuthStore();
const officialOptions = [
  { value: '', label: 'All' },
  { value: 'true', label: 'Official' },
  { value: 'false', label: 'Community' },
];
const {
  staff,
  mine,
  official,
  query,
  factions,
  records,
  count,
  nextPage,
  loading,
  loadingMore,
  error,
  moreError,
  filterQuery,
  load,
  reset,
  toggleFaction,
} = useEncounterList();
const sentinel = ref<HTMLElement | null>(null);
const visible = ref(false);
useIntersectionObserver(
  sentinel,
  (entries) => {
    visible.value = entries.some((entry) => entry.isIntersecting);
  },
  { rootMargin: '400px 0px' },
);
watch([visible, loading, loadingMore, nextPage], () => {
  if (visible.value && nextPage.value && !loading.value && !loadingMore.value && !moreError.value)
    void load(true);
});
</script>
