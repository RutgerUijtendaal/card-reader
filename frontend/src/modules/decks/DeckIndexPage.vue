<template>
  <section class="flex flex-col gap-5">
    <AppPageHeader
      :icon="activeHeaderIcon"
      :title="activeTitle"
      :subtitle="activeSubtitle"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <AppHeaderAction
          :icon="Hammer"
          label="Build a deck"
          short-label="Build a deck"
          variant="primary"
          :to="newDeckLocation"
        />
      </template>
    </AppPageHeader>

    <AppPageLayout>
      <template #aside>
        <DeckBrowseFiltersPanel
          :controller="filterController"
          :total-count="decks.length"
          :description="filterDescription"
          :mode="isOwnedMode ? 'owned' : 'public'"
          :can-use-owned-decks="canUseOwnedDecks"
          :public-to="{ path: '/decks', query: publicFilterRouteQuery }"
          :owned-to="{ path: '/my/decks', query: ownedFilterRouteQuery }"
        />
      </template>

      <div
        v-if="loading || !filtersLoaded"
        class="deck-index-grid grid gap-4"
      >
        <DeckLoadingSkeleton
          v-for="index in loadingSkeletonCount"
          :key="`deck-loading-${index}`"
        />
      </div>

      <div
        v-else-if="decks.length === 0"
        class="page-card theme-section-muted text-sm"
      >
        {{ emptyLabel }}
      </div>

      <div
        v-else
        class="deck-index-grid grid gap-4"
      >
        <DeckListCard
          v-for="deck in decks"
          :key="deck.id"
          :deck="deck"
          :mode="isOwnedMode ? 'owned' : 'browse'"
          :title-to="isOwnedMode ? `/my/decks/${deck.id}` : `/decks/${deck.id}`"
        >
          <template
            v-if="!isOwnedMode && canEditDeck(deck)"
            #menu-actions="{ close }"
          >
            <RouterLink
              class="btn-secondary app-menu-action"
              :to="buildPublicDeckEditorLocation(deck.id)"
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
            #actions
          >
            <div class="flex w-[10.75rem] flex-col items-stretch gap-3">
              <div class="flex items-center gap-2">
                <RouterLink
                  class="btn-secondary min-w-0 flex-1"
                  :to="buildMyDeckEditorLocation(deck.id)"
                >
                  Edit
                </RouterLink>
                <ExtraActionsMenu
                  button-label="Open deck actions"
                  panel-class="w-52"
                >
                  <template #default="{ close }">
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

                    <button
                      class="btn-secondary app-menu-action"
                      type="button"
                      aria-label="Playtest deck"
                      @click="goToPlaytester(deck); close()"
                    >
                      <Gamepad2
                        class="h-4 w-4 shrink-0"
                        aria-hidden="true"
                      />
                      Playtest
                    </button>

                    <button
                      v-if="canShareDeck(deck)"
                      class="btn-secondary app-menu-action"
                      type="button"
                      aria-label="Copy share link"
                      @click="copyShareLink(deck); close()"
                    >
                      <Share2
                        class="h-4 w-4 shrink-0"
                        aria-hidden="true"
                      />
                      Share
                    </button>

                    <button
                      class="btn-secondary app-menu-action"
                      type="button"
                      aria-label="Copy Mainboard TTS"
                      @click="exportDeck(deck); close()"
                    >
                      <TtsCopyIcon
                        class="h-4 w-4 shrink-0"
                        aria-hidden="true"
                      />
                      TTS
                    </button>

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
                </ExtraActionsMenu>
              </div>

              <AppSelect
                wrapper-class="min-w-0 w-full"
                :disabled="savingDeckIds.has(deck.id)"
                :model-value="deck.visibility"
                :options="visibilityOptions"
                @update:model-value="handleVisibilitySelect(deck, $event)"
              />
            </div>
          </template>
        </DeckListCard>
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
import { useDebounceFn } from '@vueuse/core';
import { BookOpen, Folders, Gamepad2, Hammer, Pencil, Share2, Tags, Trash2 } from 'lucide-vue-next';
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import AppPageLayout from '@/components/app/AppPageLayout.vue';
import AppHeaderAction from '@/components/app/AppHeaderAction.vue';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSelect from '@/components/app/AppSelect.vue';
import ExtraActionsMenu from '@/components/app/ExtraActionsMenu.vue';
import TtsCopyIcon from '@/components/icons/TtsCopyIcon.vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import {
  deleteDeck,
  fetchDeckTags,
  fetchMyDeck,
  fetchMyDeckSummaries,
  fetchPublicDeckSummaries,
  updateDeck,
} from '@/modules/decks/api';
import DeckBrowseFiltersPanel from '@/modules/decks/components/DeckBrowseFiltersPanel.vue';
import DeckLoadingSkeleton from '@/components/decks/DeckLoadingSkeleton.vue';
import DeckListCard from '@/components/decks/DeckListCard.vue';
import DeckTagManagementModal from '@/components/decks/DeckTagManagementModal.vue';
import { useDeckBrowseFilters } from '@/modules/decks/composables/useDeckBrowseFilters';
import {
  buildDeckBrowseFilterApiSearchParams,
  buildDeckBrowseFilterRouteQuery,
  getDeckBrowseFilterSignature,
  parseDeckBrowseFilterRouteQuery,
  sameDeckBrowseFilterState,
} from '@/composables/decks/deckBrowseFilterState';
import {
  buildMyDeckEditorLocation,
  buildNewDeckEditorLocation,
  buildPublicDeckEditorLocation,
} from '@/composables/decks/deckRouteState';
import { buildDeckShareUrl, canShareDeck } from '@/composables/decks/share';
import type { DeckSummaryRecord, DeckVisibility } from '@/modules/decks/types';
import { useDeckExport } from '@/composables/useDeckExport';
import { deckVisibilityLabels, deckVisibilityOptions } from '@/composables/decks/visibility';
import { getDeckTagSuggestionFeedback } from '@/composables/decks/deckTagSuggestionFeedback';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const decks = ref<DeckSummaryRecord[]>([]);
const loading = ref(false);
const deleting = ref(false);
const deleteTarget = ref<DeckSummaryRecord | null>(null);
const savingDeckIds = ref(new Set<string>());
const tagManagerTarget = ref<DeckSummaryRecord | null>(null);
const tagManagerTagIds = ref<string[]>([]);
const tagManagerSuggestedTypeLabels = ref<string[]>([]);
const tagManagerLoading = ref(false);
const tagManagerSaving = ref(false);
const tagManagerError = ref<string | null>(null);
const visibilityOptions = deckVisibilityOptions;
const { exportTtsDeck } = useDeckExport();
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
const activeHeaderIcon = computed(() => (isOwnedMode.value ? Folders : BookOpen));
const activeTitle = computed(() => (isOwnedMode.value ? 'My Decks' : 'Decks'));
const activeSubtitle = computed(() =>
  isOwnedMode.value
    ? 'Manage your private, unlisted, and public decks.'
    : 'Browse public decks and inspect their hero, mainboard, and sideboards.',
);
const filterDescription = computed(() =>
  isOwnedMode.value
    ? 'Search your decks by deck, hero, included cards, and affinity.'
    : 'Search public decks by deck, hero, owner, included cards, and affinity.',
);
const loadingSkeletonCount = 10;
const currentRouteFilterState = computed(() => parseDeckBrowseFilterRouteQuery(route.query));
const effectiveRouteFilterState = computed(() => currentRouteFilterState.value);
const publicFilterRouteQuery = computed(() => buildDeckBrowseFilterRouteQuery(currentRouteFilterState.value));
const ownedFilterRouteQuery = computed(() => buildDeckBrowseFilterRouteQuery(currentRouteFilterState.value));
const currentRouteSignature = computed(() => getDeckBrowseFilterSignature(effectiveRouteFilterState.value));
const hasActiveFilters = computed(() => currentRouteSignature.value.length > 0);
const emptyLabel = computed(() => {
  if (hasActiveFilters.value) {
    return isOwnedMode.value ? 'No owned decks match the current filters.' : 'No public decks match the current filters.';
  }
  return isOwnedMode.value ? 'You do not have any decks yet.' : 'No public decks yet.';
});
const currentDeckPath = computed(() => (isOwnedMode.value ? '/my/decks' : '/decks'));
const newDeckLocation = computed(() => buildNewDeckEditorLocation(isOwnedMode.value ? 'my_decks' : 'decks'));
let deckLoadRequestId = 0;
let tagManagerLoadRequestId = 0;

const loadDecks = async (): Promise<void> => {
  const requestId = ++deckLoadRequestId;
  const requestedPath = currentDeckPath.value;
  loading.value = true;
  try {
    const params = buildDeckBrowseFilterApiSearchParams(selectionState.value);
    const nextDecks = requestedPath === '/my/decks' ? await fetchMyDeckSummaries(params) : await fetchPublicDeckSummaries(params);
    if (requestId === deckLoadRequestId && currentDeckPath.value === requestedPath) {
      decks.value = nextDecks;
    }
  } finally {
    if (requestId === deckLoadRequestId) {
      loading.value = false;
    }
  }
};

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
    await loadDecks();
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
    closeTagManager(true);
    toast.success('Deck tags updated.');
    try {
      await loadDecks();
    } catch {
      toast.error('Deck tags were updated, but the deck list could not be refreshed.');
    }
  } catch {
    toast.error('Unable to update deck tags.');
  } finally {
    tagManagerSaving.value = false;
  }
};

const updateDeckVisibility = async (deck: DeckSummaryRecord, visibility: DeckVisibility): Promise<void> => {
  if (deck.visibility === visibility) {
    return;
  }
  savingDeckIds.value = new Set(savingDeckIds.value).add(deck.id);
  try {
    const nextDeck = await updateDeck(deck.id, { visibility });
    decks.value = decks.value.map((entry) =>
      entry.id === nextDeck.id
        ? {
            ...entry,
            visibility: nextDeck.visibility,
            status: {
              is_valid: nextDeck.status.is_valid,
              label: nextDeck.status.label,
              deprecated_card_count: nextDeck.status.deprecated_card_count,
            },
            updated_at: nextDeck.updated_at,
          }
        : entry,
    );
    toast.success(`Deck is now ${deckVisibilityLabels[nextDeck.visibility].toLowerCase()}.`);
  } catch {
    toast.error('Unable to update deck visibility.');
  } finally {
    const nextSavingDeckIds = new Set(savingDeckIds.value);
    nextSavingDeckIds.delete(deck.id);
    savingDeckIds.value = nextSavingDeckIds;
  }
};

const handleVisibilitySelect = (deck: DeckSummaryRecord, value: string | number | null): void => {
  if (value === 'private' || value === 'unlisted' || value === 'public') {
    void updateDeckVisibility(deck, value);
  }
};

const copyShareLink = async (deck: DeckSummaryRecord): Promise<void> => {
  if (!canShareDeck(deck)) {
    return;
  }
  await navigator.clipboard.writeText(buildDeckShareUrl(deck.id));
  toast.success('Share link copied.');
};

const goToPlaytester = (deck: DeckSummaryRecord): void => {
  void router.push(`/playtester/${deck.id}`);
};

const exportDeck = async (deck: DeckSummaryRecord): Promise<void> => {
  await exportTtsDeck(deck.id);
};

const confirmDelete = async (): Promise<void> => {
  if (!deleteTarget.value) return;
  deleting.value = true;
  try {
    await deleteDeck(deleteTarget.value.id);
    decks.value = decks.value.filter((deck) => deck.id !== deleteTarget.value?.id);
    deleteTarget.value = null;
    toast.success('Deck deleted.');
  } finally {
    deleting.value = false;
  }
};

onMounted(() => {
  void loadFilters().catch(() => undefined);
});
</script>

<style scoped>
.deck-index-grid {
  width: 100%;
  max-width: 72rem;
  margin-inline: auto;
  grid-template-columns: minmax(0, 1fr);
}
</style>
