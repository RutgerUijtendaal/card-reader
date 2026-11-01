<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="mine ? APP_SECTION_ICONS.myEncounters : APP_SECTION_ICONS.encounters"
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
          v-if="auth.authenticated"
          :icon="APP_SECTION_ICONS.encounterBuilder"
          label="Build Encounter"
          short-label="Build Encounter"
          variant="primary"
          to="/my/encounters/new"
        />
      </template>
      <template
        v-if="auth.authenticated"
        #center
      >
        <AppScopeTabs
          label="Encounter library"
          :tabs="scopeTabs"
        />
      </template>
      <template #bottomLeft>
        <AppCollectionToolbar>
          <template #search>
            <AppCollectionSearch
              :query="query"
              placeholder="Search Encounters by name..."
              :total-count="count"
              :result-noun="['Encounter', 'Encounters']"
              @update:query="(value) => (query = value)"
            />
          </template>
          <template #filters>
            <div
              class="theme-toggle-shell"
              role="group"
              aria-label="Official status"
            >
              <button
                v-for="option in officialOptions"
                :key="option.value"
                type="button"
                class="theme-toggle-option"
                :class="{ 'theme-toggle-option-active': official === option.value }"
                :aria-pressed="official === option.value"
                @click="official = option.value"
              >
                {{ option.label }}
              </button>
            </div>
            <span
              class="theme-divider mx-1 h-5 border-l"
              aria-hidden="true"
            />
            <div
              class="flex flex-wrap items-center gap-2"
              role="group"
              aria-label="Factions"
            >
              <ChoicePill
                v-for="option in CARD_FACTION_OPTIONS"
                :key="option.value"
                :selected="factions.includes(option.value)"
                @click="toggleFaction(option.value)"
              >
                {{ option.label }}
              </ChoicePill>
            </div>
            <button
              v-if="hasActiveFilters"
              type="button"
              class="theme-ghost-button inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-sm font-medium"
              @click="reset"
            >
              <X
                class="h-3.5 w-3.5"
                aria-hidden="true"
              />
              Clear filters
            </button>
          </template>
        </AppCollectionToolbar>
      </template>
    </AppPageHeader>
    <AppPageLayout columns="one">
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
      <AppEmptyState
        v-else-if="!records.length"
        :icon="mine ? APP_SECTION_ICONS.myEncounters : APP_SECTION_ICONS.encounters"
        :title="
          hasActiveFilters
            ? 'No Encounters match the current filters.'
            : staff || mine
              ? 'No saved Encounters yet.'
              : 'No public Encounters yet.'
        "
        :message="
          hasActiveFilters
            ? 'Try removing a filter or searching for something else.'
            : mine
              ? 'Pick a boss and build an Evil deck to challenge players.'
              : 'Encounters that players publish appear here.'
        "
      >
        <button
          v-if="hasActiveFilters"
          class="btn-secondary"
          type="button"
          @click="reset"
        >
          Clear filters
        </button>
        <RouterLink
          v-else-if="auth.authenticated"
          class="btn-primary"
          to="/my/encounters/new"
        >
          Build Encounter
        </RouterLink>
      </AppEmptyState>
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
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { X } from 'lucide-vue-next';
import { useIntersectionObserver } from '@vueuse/core';
import { CARD_FACTION_OPTIONS } from '@/domain/cards/cardFactions';
import { useAuthStore } from '@/domain/session/store';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppCollectionSearch from '@/shared/components/app/AppCollectionSearch.vue';
import AppCollectionToolbar from '@/shared/components/app/AppCollectionToolbar.vue';
import AppEmptyState from '@/shared/components/app/AppEmptyState.vue';
import AppScopeTabs, { type AppScopeTab } from '@/shared/components/app/AppScopeTabs.vue';
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
const hasActiveFilters = computed(() => Boolean(query.value || factions.value.length || official.value));
const scopeTabs = computed<AppScopeTab[]>(() => [
  {
    label: 'Public',
    to: { path: '/encounters', query: filterQuery.value },
    active: !staff.value && !mine.value,
    icon: APP_SECTION_ICONS.encounters,
  },
  {
    label: 'My Encounters',
    to: { path: '/my/encounters', query: filterQuery.value },
    active: mine.value,
    icon: APP_SECTION_ICONS.myEncounters,
  },
  ...(auth.canAccessStaffRoutes
    ? [
        {
          label: 'All',
          to: { path: '/staff/encounters', query: filterQuery.value },
          active: staff.value,
          icon: APP_SECTION_ICONS.admin,
        },
      ]
    : []),
]);
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
