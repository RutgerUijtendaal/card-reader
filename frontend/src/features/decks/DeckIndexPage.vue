<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="APP_SECTION_ICONS.decks"
      title="Decks"
      subtitle="Browse published decks and manage your own."
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <AppHeaderAction
          :icon="APP_SECTION_ICONS.deckBuilder"
          label="Build a deck"
          short-label="Build a deck"
          variant="primary"
          :to="newDeckLocation"
        />
      </template>
      <template #bottomLeft>
        <AppCollectionToolbar>
          <template #search>
            <AppCollectionSearch
              :query="filterController.query.value"
              :placeholder="searchPlaceholder"
              :total-count="totalDeckCount"
              :result-noun="['deck', 'decks']"
              @update:query="filterController.updateQuery"
            />
          </template>
          <template #filters>
            <AppScopeToggle
              v-if="canUseOwnedDecks"
              label="Deck library"
              :options="scopeOptions"
            />
            <span
              v-if="canUseOwnedDecks"
              class="theme-divider mx-1 h-5 border-l"
              aria-hidden="true"
            />
            <DeckBrowseFilterBar
              :controller="filterController"
              :has-active-filters="hasActiveFilters"
            />
          </template>
        </AppCollectionToolbar>
      </template>
    </AppPageHeader>

    <AppPageLayout columns="one">
      <div
        v-if="(loading && decks.length === 0) || !filtersLoaded"
        class="app-page-collection-grid grid gap-4"
      >
        <CollectionTileSkeleton
          v-for="index in loadingSkeletonCount"
          :key="`deck-loading-${index}`"
        />
      </div>

      <div
        v-else-if="initialLoadError"
        class="page-card theme-section-muted flex items-center justify-between gap-3 text-sm"
      >
        <span>{{ initialLoadError }}</span>
        <button
          type="button"
          class="btn-secondary px-3 py-2 text-xs"
          @click="refreshDecks"
        >
          Retry
        </button>
      </div>

      <AppEmptyState
        v-else-if="decks.length === 0"
        :icon="activeHeaderIcon"
        :title="emptyLabel"
        :message="emptyMessage"
      >
        <button
          v-if="hasActiveFilters"
          class="btn-secondary"
          type="button"
          @click="filterController.resetFilters"
        >
          Clear filters
        </button>
        <RouterLink
          v-else-if="auth.authenticated"
          class="btn-primary"
          :to="newDeckLocation"
        >
          Build a deck
        </RouterLink>
      </AppEmptyState>

      <div
        v-else
        class="app-page-collection-grid grid gap-4"
      >
        <DeckListCard
          v-for="deck in decks"
          :key="deck.id"
          :deck="deck"
          :mode="isOwnedMode ? 'owned' : 'browse'"
          :title-to="isOwnedMode ? `/my/decks/${deck.id}` : `/decks/${deck.id}`"
        >
          <template
            v-if="isOwnedMode || canEditDeck(deck)"
            #menu-actions="{ close }"
          >
            <RouterLink
              class="btn-secondary app-menu-action"
              :to="isOwnedMode ? buildMyDeckEditorLocation(deck.id) : buildPublicDeckEditorLocation(deck.id)"
              aria-label="Edit deck"
              @click="close"
            >
              <Pencil
                class="h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              Edit
            </RouterLink>

            <button
              class="btn-secondary app-menu-action"
              type="button"
              aria-label="Manage deck tags"
              @click="openTagManager(deck, close)"
            >
              <Tags
                class="h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              Tags
            </button>
          </template>

          <template
            v-if="isOwnedMode"
            #menu-danger-actions="{ close }"
          >
            <button
              class="btn-danger-secondary app-menu-action"
              type="button"
              aria-label="Delete deck"
              @click="promptDelete(deck); close()"
            >
              <Trash2
                class="h-4 w-4 shrink-0"
                aria-hidden="true"
              />
              Delete
            </button>
          </template>
        </DeckListCard>
      </div>

      <div
        v-if="filtersLoaded && decks.length > 0"
        ref="loadMoreSentinelRef"
        class="app-page-single-column theme-divider mt-5 flex min-h-16 items-center justify-center border-t pt-4"
        data-testid="deck-load-more-sentinel"
        aria-live="polite"
      >
        <div
          v-if="loadingNextPage"
          class="app-page-collection-grid grid w-full gap-4"
        >
          <CollectionTileSkeleton
            v-for="index in 3"
            :key="`deck-next-${index}`"
          />
        </div>
        <div
          v-else-if="loadMoreError"
          class="flex items-center gap-3"
        >
          <span class="theme-section-muted text-xs">{{ loadMoreError }}</span>
          <button
            type="button"
            class="btn-secondary px-3 py-2 text-xs"
            @click="retryNextPage"
          >
            Retry
          </button>
        </div>
        <span
          v-else-if="nextPage !== null"
          class="theme-section-muted text-xs"
        >
          Loading more decks…
        </span>
        <span
          v-else
          class="theme-section-muted text-xs"
        >
          All {{ totalDeckCount }} decks loaded.
        </span>
      </div>
    </AppPageLayout>

    <ConfirmModal
      :open="deleteTarget !== null"
      title="Delete Deck"
      :message="deleteTarget ? `Delete deck '${deleteTarget.name}'?` : ''"
      confirm-label="Delete"
      cancel-label="Cancel"
      :loading="deleting"
      loading-label="Deleting..."
      @cancel="deleteTarget = null"
      @confirm="confirmDelete"
    />

    <DeckTagManagementModal
      :open="tagManagerTarget !== null"
      :deck-name="tagManagerTarget?.name ?? ''"
      :catalog="deckTags"
      :model-value="tagManagerTagIds"
      :suggested-type-labels="tagManagerSuggestedTypeLabels"
      :loading="tagManagerLoading"
      :saving="tagManagerSaving"
      :error-message="tagManagerError"
      @update:model-value="tagManagerTagIds = $event"
      @update:suggested-type-labels="tagManagerSuggestedTypeLabels = $event"
      @save="saveManagedDeckTags"
      @cancel="closeTagManager"
      @retry="loadTagManager"
    />
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn, useIntersectionObserver } from '@vueuse/core';
import { Pencil, Tags, Trash2 } from 'lucide-vue-next';
import { computed, nextTick, onMounted, ref, shallowRef, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import AppCollectionSearch from '@/shared/components/app/AppCollectionSearch.vue';
import AppCollectionToolbar from '@/shared/components/app/AppCollectionToolbar.vue';
import AppEmptyState from '@/shared/components/app/AppEmptyState.vue';
import AppScopeToggle, { type AppScopeOption } from '@/shared/components/app/AppScopeToggle.vue';
import ConfirmModal from '@/shared/components/modals/ConfirmModal.vue';
import { useAuthStore } from '@/domain/session/store';
import {
  deleteDeck,
  fetchDeckTags,
  fetchMyDeck,
  fetchMyDeckSummaryPage,
  fetchPublicDeckSummaryPage,
  updateDeck,
} from '@/domain/decks/api';
import DeckBrowseFilterBar from '@/features/decks/components/DeckBrowseFilterBar.vue';
import CollectionTileSkeleton from '@/shared/components/CollectionTileSkeleton.vue';
import DeckListCard from '@/domain/decks/components/DeckListCard.vue';
import DeckTagManagementModal from '@/domain/decks/components/DeckTagManagementModal.vue';
import { useDeckBrowseFilters } from '@/features/decks/composables/useDeckBrowseFilters';
import {
  buildDeckBrowseFilterApiSearchParams,
  buildDeckBrowseFilterRouteQuery,
  getDeckBrowseFilterSignature,
  parseDeckBrowseFilterRouteQuery,
  sameDeckBrowseFilterState,
} from '@/domain/decks/utils/deckBrowseFilterState';
import {
  buildMyDeckEditorLocation,
  buildNewDeckEditorLocation,
  buildPublicDeckEditorLocation,
} from '@/domain/decks/utils/deckRouteState';
import type { DeckRecord, DeckSummaryCursor, DeckSummaryRecord } from '@/domain/decks/types';
import { getDeckTagSuggestionFeedback } from '@/domain/decks/utils/deckTagSuggestionFeedback';
import {
  appendGalleryPage,
  createEmptyGalleryPageState,
  replaceGalleryPage,
} from '@/domain/cards/utils/gallery/galleryState';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const deckPageState = shallowRef(createEmptyGalleryPageState<DeckSummaryRecord>());
const decks = computed(() => deckPageState.value.cards);
const totalDeckCount = computed(() => deckPageState.value.count);
const nextPage = computed(() => deckPageState.value.nextPage);
const deckSnapshotAt = ref<string | null>(null);
const deckNextCursor = ref<DeckSummaryCursor | null>(null);
const pageSize = 10;
const loading = ref(false);
const loadingNextPage = ref(false);
const initialLoadError = ref<string | null>(null);
const loadMoreError = ref<string | null>(null);
const loadMoreSentinelRef = ref<HTMLElement | null>(null);
const loadMoreSentinelIsIntersecting = ref(false);
const deleting = ref(false);
const deleteTarget = ref<DeckSummaryRecord | null>(null);
const tagManagerTarget = ref<DeckSummaryRecord | null>(null);
const tagManagerTagIds = ref<string[]>([]);
const tagManagerSuggestedTypeLabels = ref<string[]>([]);
const tagManagerLoading = ref(false);
const tagManagerSaving = ref(false);
const tagManagerError = ref<string | null>(null);
const filterController = useDeckBrowseFilters();
const {
  filtersLoaded,
  deckTags,
  selectionState,
  readFilterState,
  applyRouteFilterState,
  loadFilters,
} = filterController;

const isOwnedMode = computed(() => route.path === '/my/decks');
const canUseOwnedDecks = computed(() => auth.authenticated || isOwnedMode.value);
const activeHeaderIcon = computed(() => (
  isOwnedMode.value ? APP_SECTION_ICONS.myDecks : APP_SECTION_ICONS.decks
));
const searchPlaceholder = computed(() =>
  isOwnedMode.value
    ? 'Search your decks, heroes, or cards...'
    : 'Search public decks, heroes, owners, or cards...',
);
const loadingSkeletonCount = 9;
const currentRouteFilterState = computed(() => parseDeckBrowseFilterRouteQuery(route.query));
const effectiveRouteFilterState = computed(() => currentRouteFilterState.value);
const scopeFilterRouteQuery = computed(() => buildDeckBrowseFilterRouteQuery(currentRouteFilterState.value));
const scopeOptions = computed<AppScopeOption[]>(() => [
  {
    label: 'Public',
    to: { path: '/decks', query: scopeFilterRouteQuery.value },
    active: !isOwnedMode.value,
  },
  {
    label: 'Mine',
    to: { path: '/my/decks', query: scopeFilterRouteQuery.value },
    active: isOwnedMode.value,
  },
]);
const currentRouteSignature = computed(() => getDeckBrowseFilterSignature(effectiveRouteFilterState.value));
const hasActiveFilters = computed(() => currentRouteSignature.value.length > 0);
const emptyLabel = computed(() => {
  if (hasActiveFilters.value) {
    return isOwnedMode.value ? 'No owned decks match the current filters.' : 'No public decks match the current filters.';
  }
  return isOwnedMode.value ? 'You do not have any decks yet.' : 'No public decks yet.';
});
const emptyMessage = computed(() => {
  if (hasActiveFilters.value) {
    return 'Try removing a filter or searching for something else.';
  }
  return isOwnedMode.value
    ? 'Build your first deck from a hero and the cards in the Player gallery.'
    : 'Decks that players publish appear here.';
});
const currentDeckPath = computed(() => (isOwnedMode.value ? '/my/decks' : '/decks'));
const newDeckLocation = computed(() => buildNewDeckEditorLocation(isOwnedMode.value ? 'my_decks' : 'decks'));
let deckLoadRequestId = 0;
let tagManagerLoadRequestId = 0;

const loadDecksPage = async (page: number, mode: 'replace' | 'append'): Promise<boolean> => {
  const requestId = ++deckLoadRequestId;
  const requestedPath = currentDeckPath.value;
  const requestedSignature = currentRouteSignature.value;
  const requestedSnapshotAt = mode === 'append' ? deckSnapshotAt.value : null;
  const requestedCursor = mode === 'append' ? deckNextCursor.value : null;
  if (mode === 'replace') {
    loading.value = true;
    loadingNextPage.value = false;
    initialLoadError.value = null;
    loadMoreError.value = null;
  } else {
    loadingNextPage.value = true;
    loadMoreError.value = null;
  }
  try {
    const params = buildDeckBrowseFilterApiSearchParams(selectionState.value);
    const response =
      requestedPath === '/my/decks'
        ? await fetchMyDeckSummaryPage(params, page, pageSize, requestedSnapshotAt, requestedCursor)
        : await fetchPublicDeckSummaryPage(params, page, pageSize, requestedSnapshotAt, requestedCursor);
    if (
      requestId === deckLoadRequestId &&
      currentDeckPath.value === requestedPath &&
      currentRouteSignature.value === requestedSignature
    ) {
      deckPageState.value = mode === 'replace'
        ? replaceGalleryPage(response)
        : appendGalleryPage(deckPageState.value, response);
      deckSnapshotAt.value = response.snapshot_at;
      deckNextCursor.value = response.next_cursor;
      return true;
    }
  } catch {
    if (requestId === deckLoadRequestId) {
      if (mode === 'replace') {
        if (deckPageState.value.cards.length === 0) {
          initialLoadError.value = 'Unable to load decks.';
        }
      } else {
        loadMoreError.value = 'Unable to load more decks.';
      }
    }
  } finally {
    if (requestId === deckLoadRequestId) {
      if (mode === 'replace') {
        loading.value = false;
      } else {
        loadingNextPage.value = false;
      }
    }
  }
  return false;
};

const scheduleNextPageIfVisible = (): void => {
  void nextTick().then(() => {
    if (loadMoreSentinelIsIntersecting.value && nextPage.value !== null) {
      void loadNextPage();
    }
  });
};

const refreshDecks = async (): Promise<boolean> => {
  const loaded = await loadDecksPage(1, 'replace');
  if (loaded) {
    scheduleNextPageIfVisible();
  }
  return loaded;
};

const loadNextPage = async (): Promise<void> => {
  if (loading.value || loadingNextPage.value || loadMoreError.value || nextPage.value === null) {
    return;
  }
  if (await loadDecksPage(nextPage.value, 'append')) {
    scheduleNextPageIfVisible();
  }
};

const retryNextPage = (): void => {
  loadMoreError.value = null;
  void loadNextPage();
};

useIntersectionObserver(
  loadMoreSentinelRef,
  (entries) => {
    loadMoreSentinelIsIntersecting.value = entries.some((entry) => entry.isIntersecting);
    if (loadMoreSentinelIsIntersecting.value) {
      void loadNextPage();
    }
  },
  { rootMargin: '400px 0px' },
);

const debouncedUpdateRoute = useDebounceFn(() => {
  if (!filtersLoaded.value) {
    return;
  }
  const nextRouteState = readFilterState();
  const effectiveNextRouteState = nextRouteState;
  if (sameDeckBrowseFilterState(effectiveNextRouteState, effectiveRouteFilterState.value)) {
    return;
  }
  void router.replace({
    path: currentDeckPath.value,
    query: buildDeckBrowseFilterRouteQuery(effectiveNextRouteState),
  });
}, 250);

watch(
  selectionState,
  () => {
    debouncedUpdateRoute();
  },
  { deep: true },
);

watch(
  [currentDeckPath, currentRouteSignature, filtersLoaded],
  async ([, , ready]) => {
    if (!ready) {
      return;
    }
    const routeState = effectiveRouteFilterState.value;
    if (!sameDeckBrowseFilterState(readFilterState(), routeState)) {
      applyRouteFilterState(routeState);
    }
    deckPageState.value = createEmptyGalleryPageState<DeckSummaryRecord>();
    deckSnapshotAt.value = null;
    deckNextCursor.value = null;
    initialLoadError.value = null;
    loadMoreError.value = null;
    await refreshDecks();
  },
  { immediate: true },
);

const promptDelete = (deck: DeckSummaryRecord): void => {
  deleteTarget.value = deck;
};

const canEditDeck = (deck: DeckSummaryRecord): boolean =>
  isOwnedMode.value
  || auth.user?.id === deck.owner.id
  || auth.canAccessStaffRoutes;

const loadTagManager = async (): Promise<void> => {
  const target = tagManagerTarget.value;
  if (!target) {
    return;
  }
  const requestId = ++tagManagerLoadRequestId;
  tagManagerLoading.value = true;
  tagManagerError.value = null;
  try {
    const hasCatalog = deckTags.value.roles.length > 0 || deckTags.value.types.length > 0;
    const [record, catalog] = await Promise.all([
      fetchMyDeck(target.id),
      hasCatalog ? Promise.resolve(deckTags.value) : fetchDeckTags(),
    ]);
    if (requestId !== tagManagerLoadRequestId || tagManagerTarget.value?.id !== target.id) {
      return;
    }
    deckTags.value = catalog;
    tagManagerTagIds.value = (record.tags ?? []).map((tag) => tag.id);
    tagManagerSuggestedTypeLabels.value = (record.pending_tag_suggestions ?? []).map(
      (suggestion) => suggestion.label,
    );
  } catch {
    if (requestId === tagManagerLoadRequestId && tagManagerTarget.value?.id === target.id) {
      tagManagerError.value = 'Unable to load deck tags.';
    }
  } finally {
    if (requestId === tagManagerLoadRequestId) {
      tagManagerLoading.value = false;
    }
  }
};

const openTagManager = (deck: DeckSummaryRecord, closeMenu: () => void): void => {
  closeMenu();
  tagManagerTarget.value = deck;
  tagManagerTagIds.value = [];
  tagManagerSuggestedTypeLabels.value = [];
  tagManagerError.value = null;
  void loadTagManager();
};

const closeTagManager = (force = false): void => {
  if (tagManagerSaving.value && !force) {
    return;
  }
  tagManagerLoadRequestId += 1;
  tagManagerTarget.value = null;
  tagManagerTagIds.value = [];
  tagManagerSuggestedTypeLabels.value = [];
  tagManagerError.value = null;
  tagManagerLoading.value = false;
};

const applyUpdatedDeckRecord = (nextDeck: DeckRecord): void => {
  deckPageState.value = {
    ...deckPageState.value,
    cards: deckPageState.value.cards.map((entry) =>
      entry.id === nextDeck.id
        ? {
            ...entry,
            difficulty: nextDeck.difficulty,
            visibility: nextDeck.visibility,
            tags: nextDeck.tags,
            pending_tag_suggestions: nextDeck.pending_tag_suggestions,
            status: {
              is_valid: nextDeck.status.is_valid,
              label: nextDeck.status.label,
              deprecated_card_count: nextDeck.status.deprecated_card_count,
            },
            updated_at: nextDeck.updated_at,
          }
        : entry,
    ),
  };
};

const saveManagedDeckTags = async (): Promise<void> => {
  const target = tagManagerTarget.value;
  if (!target || tagManagerLoading.value || tagManagerSaving.value || tagManagerError.value) {
    return;
  }
  tagManagerSaving.value = true;
  try {
    const record = await updateDeck(target.id, {
      tag_ids: [...tagManagerTagIds.value],
      suggested_type_labels: [...tagManagerSuggestedTypeLabels.value],
    });
    const feedback = getDeckTagSuggestionFeedback(record.tag_suggestion_results);
    if (feedback) {
      toast.info(feedback);
    }
    applyUpdatedDeckRecord(record);
    closeTagManager(true);
    toast.success('Deck tags updated.');
    if (!(await refreshDecks())) {
      toast.error('Deck tags were updated, but the deck list could not be refreshed.');
    }
  } catch {
    toast.error('Unable to update deck tags.');
  } finally {
    tagManagerSaving.value = false;
  }
};

const confirmDelete = async (): Promise<void> => {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    const deletedDeckId = deleteTarget.value.id;
    await deleteDeck(deletedDeckId);
    deleteTarget.value = null;
    deckPageState.value = {
      ...deckPageState.value,
      cards: deckPageState.value.cards.filter((deck) => deck.id !== deletedDeckId),
      count: Math.max(0, deckPageState.value.count - 1),
    };
    toast.success('Deck deleted.');
    if (!(await refreshDecks())) {
      toast.error('Deck deleted, but the deck list could not be refreshed.');
    }
  } finally {
    deleting.value = false;
  }
};

onMounted(() => {
  void loadFilters().catch(() => undefined);
});
</script>
