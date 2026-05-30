<template>
  <section class="flex h-[calc(100vh-3rem)] min-h-0 flex-col gap-5 overflow-hidden">
    <AppPageHeader
      :icon="activeHeaderIcon"
      :title="activeTitle"
      :subtitle="activeSubtitle"
      title-tag="h2"
      title-class="text-xl"
    >
      <template #actions>
        <div class="flex flex-wrap items-center justify-end gap-2">
          <div class="theme-tablist">
            <RouterLink
              class="theme-tab"
              :class="{ 'theme-tab-active': !isOwnedMode }"
              :to="{ path: '/decks', query: currentFilterRouteQuery }"
            >
              Public
            </RouterLink>
            <RouterLink
              v-if="canUseOwnedDecks"
              class="theme-tab"
              :class="{ 'theme-tab-active': isOwnedMode }"
              :to="{ path: '/my/decks', query: currentFilterRouteQuery }"
            >
              My Decks
            </RouterLink>
          </div>

          <RouterLink
            v-if="canUseOwnedDecks"
            class="btn-primary"
            :to="newDeckLocation"
          >
            New Deck
          </RouterLink>
        </div>
      </template>
    </AppPageHeader>

    <section class="grid min-h-0 flex-1 gap-6 overflow-hidden xl:grid-cols-[23rem_minmax(0,1fr)]">
      <DeckBrowseFiltersPanel
        :controller="filterController"
        :total-count="decks.length"
        :description="filterDescription"
      />

      <div class="app-scrollbar min-h-0 overflow-y-auto pr-1">
        <div
          v-if="loading || !filtersLoaded"
          class="deck-index-grid grid gap-4 px-1 pb-3 pt-2"
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
          class="deck-index-grid grid gap-4 px-1 pb-3 pt-2"
        >
          <DeckListCard
            v-for="deck in decks"
            :key="deck.id"
            :deck="deck"
            :mode="isOwnedMode ? 'owned' : 'browse'"
            :title-to="isOwnedMode ? `/my/decks/${deck.id}` : `/decks/${deck.id}`"
          >
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
                  <ExtraActionsMenu button-label="Open deck actions">
                    <template #default="{ close }">
                      <button
                        v-if="canShareDeck(deck)"
                        class="btn-secondary w-full justify-center"
                        type="button"
                        @click="copyShareLink(deck); close()"
                      >
                        Copy Share Link
                      </button>

                      <button
                        class="btn-secondary w-full justify-center"
                        type="button"
                        @click="exportDeck(deck); close()"
                      >
                        Export TTS
                      </button>

                      <button
                        class="btn-danger-secondary w-full justify-center"
                        type="button"
                        @click="promptDelete(deck); close()"
                      >
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
      </div>
    </section>

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
  </section>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core';
import { BookOpen, Folders } from 'lucide-vue-next';
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { useRoute, useRouter } from 'vue-router';
import AppPageHeader from '@/components/app/AppPageHeader.vue';
import AppSelect from '@/components/app/AppSelect.vue';
import ExtraActionsMenu from '@/components/app/ExtraActionsMenu.vue';
import ConfirmModal from '@/components/modals/ConfirmModal.vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { deleteDeck, fetchMyDecks, fetchPublicDecks, updateDeck } from '@/modules/decks/api';
import DeckBrowseFiltersPanel from '@/modules/decks/components/DeckBrowseFiltersPanel.vue';
import DeckLoadingSkeleton from '@/modules/decks/components/DeckLoadingSkeleton.vue';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import { useDeckBrowseFilters } from '@/modules/decks/composables/useDeckBrowseFilters';
import {
  buildDeckBrowseFilterApiSearchParams,
  buildDeckBrowseFilterRouteQuery,
  getDeckBrowseFilterSignature,
  parseDeckBrowseFilterRouteQuery,
  sameDeckBrowseFilterState,
} from '@/modules/decks/deckBrowseFilterState';
import { buildDeckUpsertRequestFromRecord } from '@/modules/decks/deckPayload';
import { buildMyDeckEditorLocation, buildNewDeckEditorLocation } from '@/modules/decks/deckRouteState';
import { buildDeckShareUrl, canShareDeck } from '@/modules/decks/share';
import type { DeckRecord, DeckVisibility } from '@/modules/decks/types';
import { useDeckExport } from '@/modules/decks/useDeckExport';
import { deckVisibilityLabels, deckVisibilityOptions } from '@/modules/decks/visibility';

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const decks = ref<DeckRecord[]>([]);
const loading = ref(false);
const deleting = ref(false);
const deleteTarget = ref<DeckRecord | null>(null);
const savingDeckIds = ref(new Set<string>());
const visibilityOptions = deckVisibilityOptions;
const { exportTtsDeck } = useDeckExport();
const filterController = useDeckBrowseFilters();
const { filtersLoaded, selectionState, readFilterState, applyRouteFilterState, loadFilters } = filterController;

const isOwnedMode = computed(() => route.path === '/my/decks');
const canUseOwnedDecks = computed(() => auth.authenticated || !auth.authEnabled || isOwnedMode.value);
const activeHeaderIcon = computed(() => (isOwnedMode.value ? Folders : BookOpen));
const activeTitle = computed(() => (isOwnedMode.value ? 'My Decks' : 'Decks'));
const activeSubtitle = computed(() =>
  isOwnedMode.value
    ? 'Manage your private, unlisted, and public decks.'
    : 'Browse public decks and inspect their hero, mainboard, and sideboards.',
);
const filterDescription = computed(() =>
  isOwnedMode.value
    ? 'Filter your decks by hero, author, included cards, and affinity.'
    : 'Filter public decks by hero, author, included cards, and affinity.',
);
const loadingSkeletonCount = 10;
const currentRouteFilterState = computed(() => parseDeckBrowseFilterRouteQuery(route.query));
const currentFilterRouteQuery = computed(() => buildDeckBrowseFilterRouteQuery(currentRouteFilterState.value));
const currentRouteSignature = computed(() => getDeckBrowseFilterSignature(currentRouteFilterState.value));
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

const loadDecks = async (): Promise<void> => {
  const requestId = ++deckLoadRequestId;
  const requestedPath = currentDeckPath.value;
  loading.value = true;
  try {
    const params = buildDeckBrowseFilterApiSearchParams(selectionState.value);
    const nextDecks = requestedPath === '/my/decks' ? await fetchMyDecks(params) : await fetchPublicDecks(params);
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
  if (sameDeckBrowseFilterState(nextRouteState, currentRouteFilterState.value)) {
    return;
  }
  void router.replace({
    path: currentDeckPath.value,
    query: buildDeckBrowseFilterRouteQuery(nextRouteState),
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
    const routeState = currentRouteFilterState.value;
    if (!sameDeckBrowseFilterState(readFilterState(), routeState)) {
      applyRouteFilterState(routeState);
    }
    await loadDecks();
  },
  { immediate: true },
);

const promptDelete = (deck: DeckRecord): void => {
  deleteTarget.value = deck;
};

const updateDeckVisibility = async (deck: DeckRecord, visibility: DeckVisibility): Promise<void> => {
  if (deck.visibility === visibility) {
    return;
  }
  savingDeckIds.value = new Set(savingDeckIds.value).add(deck.id);
  try {
    const nextDeck = await updateDeck(deck.id, {
      ...buildDeckUpsertRequestFromRecord(deck),
      visibility,
    });
    decks.value = decks.value.map((entry) => (entry.id === nextDeck.id ? nextDeck : entry));
    toast.success(`Deck is now ${deckVisibilityLabels[nextDeck.visibility].toLowerCase()}.`);
  } catch {
    toast.error('Unable to update deck visibility.');
  } finally {
    const nextSavingDeckIds = new Set(savingDeckIds.value);
    nextSavingDeckIds.delete(deck.id);
    savingDeckIds.value = nextSavingDeckIds;
  }
};

const handleVisibilitySelect = (deck: DeckRecord, value: string | number | null): void => {
  if (value === 'private' || value === 'unlisted' || value === 'public') {
    void updateDeckVisibility(deck, value);
  }
};

const copyShareLink = async (deck: DeckRecord): Promise<void> => {
  if (!canShareDeck(deck)) {
    return;
  }
  await navigator.clipboard.writeText(buildDeckShareUrl(deck.id));
  toast.success('Share link copied.');
};

const exportDeck = async (deck: DeckRecord): Promise<void> => {
  await exportTtsDeck(deck.id, deck.name);
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
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 44rem), 1fr));
}
</style>
