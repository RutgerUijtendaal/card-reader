<template>
  <CardCollectionDetailLoadingSkeleton
    v-if="loading"
    resource-label="Encounter"
    :icon="APP_SECTION_ICONS.encounters"
    :show-statistics="false"
    :back-to="backLink"
    back-label="Back to Encounters"
    :grid-style="gridStyle"
    :card-style="cardStyle"
    :group-by-type="groupByType"
  />
  <section
    v-else
    class="flex flex-col gap-5"
  >
    <AppPageHeader
      :icon="APP_SECTION_ICONS.encounters"
      :title="record?.name || 'Untitled Encounter'"
      :back-to="backLink"
      back-label="Back to Encounters"
      title-tag="h2"
      title-class="text-xl"
      :backdrop-image-url="bossImageUrl"
    >
      <template
        v-if="record"
        #subtitle
      >
        <p class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span data-testid="encounter-creator">
            By <span class="theme-section-title font-medium">{{ record.creator.username }}</span>
          </span>
          <template v-if="record.boss_card">
            <span aria-hidden="true">·</span>
            <span>{{ record.boss_card.name }}</span>
          </template>
        </p>
      </template>
      <template
        v-if="record && (record.is_official || record.factions.length > 0)"
        #details
      >
        <div class="flex flex-wrap gap-1.5">
          <span
            v-if="record.is_official"
            class="theme-pill theme-pill-accent text-xs"
          >Official</span>
          <span
            v-for="faction in record.factions"
            :key="faction"
            class="theme-pill theme-pill-neutral text-xs"
          >{{ cardFactionLabel(faction) }}</span>
        </div>
      </template>
      <template
        v-if="record"
        #actions
      >
        <AppHeaderAction
          :icon="TtsCopyIcon"
          :label="
            exporting ? 'Exporting' : activeSideboard ? 'Copy Sideboard TTS' : 'Copy Encounter TTS'
          "
          short-label="TTS"
          :disabled="exporting"
          @click="copyExport"
        />
        <AppHeaderAction
          v-if="record.can_edit"
          :icon="Pencil"
          label="Edit Encounter"
          short-label="Edit"
          :to="`/my/encounters/${record.id}/edit`"
        />
        <ExtraActionsMenu
          v-if="record.can_delete"
          button-label="More Encounter actions"
        >
          <template #default="{ close }">
            <button
              class="btn-secondary app-menu-action"
              type="button"
              @click="
                close();
                remove();
              "
            >
              <Trash2 class="h-4 w-4" />Delete
            </button>
          </template>
        </ExtraActionsMenu>
      </template>
      <template
        v-if="record"
        #bottomLeft
      >
        <AppBoardTabs
          v-model="activeView"
          label="Encounter boards"
          :tabs="boardTabs"
        />
      </template>
      <template
        v-if="record"
        #bottomRight
      >
        <span class="theme-section-muted text-sm tabular-nums">
          {{ record.total_cards + record.boss_cards.length }} cards including boss
        </span>
        <CardCollectionLayoutToggle v-model="layout" />
        <CardCollectionViewOptions
          v-model:card-scale="cardScale"
          v-model:group-by-type="groupByType"
          :sort-surface="sortSurface"
          :hover-surface="hoverSurface"
        />
      </template>
    </AppPageHeader>
    <div
      v-if="error"
      class="app-page-content theme-error-text"
      role="alert"
    >
      {{ error }}
    </div>
    <p
      v-if="record?.is_official && !record.can_edit && String(auth.user?.id) === record.creator.id"
      class="app-page-content theme-section-muted text-sm"
    >
      This is an Official Encounter. Only staff can edit or delete it. It remains in My Encounters.
    </p>
    <CollectionDetailLayout v-if="record">
      <template #aside>
        <div class="space-y-4">
          <h3 class="theme-section-title text-base font-semibold">
            Boss
          </h3>
          <div class="space-y-3">
            <component
              :is="record.boss_card ? RouterLink : 'div'"
              :to="record.boss_card ? cardLocation(record.boss_card.id) : undefined"
              :aria-label="record.boss_card ? `Open ${record.boss_card.name}` : undefined"
              class="theme-card-frame theme-card-image-well mx-auto block aspect-[63/88] w-full max-w-[22rem] overflow-hidden rounded-2xl"
              data-testid="encounter-boss-card"
            >
              <img
                v-if="bossImageUrl && record.boss_card"
                :src="bossImageUrl"
                :alt="record.boss_card.name"
                class="h-full w-full object-cover"
              >
              <div
                v-else
                class="theme-kicker flex h-full items-center justify-center text-xs"
              >
                {{ record.boss_card ? 'No image' : 'No boss selected' }}
              </div>
            </component>
          </div>
          <section
            class="theme-divider space-y-2 border-t pt-4"
            data-testid="encounter-summary"
          >
            <h4 class="theme-section-title text-sm font-semibold">
              Summary
            </h4>
            <CardMarkupText
              v-if="record.description_markup || record.description"
              class="theme-section-muted text-sm"
              :markup="record.description_markup || record.description"
              :hover-mode="hoverSurface.effectiveHoverMode.value"
            />
            <p
              v-else
              class="theme-section-muted text-sm leading-6"
            >
              No description provided.
            </p>
            <button
              v-if="hasLongDescription && !aboutOpen"
              type="button"
              class="theme-link text-sm font-semibold"
              @click="activeView = ABOUT_VIEW"
            >
              Read the full description
            </button>
          </section>
          <section class="theme-divider space-y-3 border-t pt-4">
            <div class="flex flex-wrap gap-2">
              <span class="theme-pill theme-pill-neutral text-xs">{{ record.total_cards }} deck cards</span>
              <span
                v-if="auth.canAccessStaffRoutes || String(auth.user?.id) === record.creator.id"
                class="theme-pill text-xs"
                :class="
                  record.visibility === 'public' ? 'theme-pill-success' : 'theme-pill-neutral'
                "
              >{{ record.visibility.charAt(0).toUpperCase() + record.visibility.slice(1) }}</span>
              <span
                v-if="!record.status.is_valid"
                class="theme-pill theme-pill-warning text-xs"
              >Under construction</span>
            </div>
            <ul
              v-if="!record.status.is_valid"
              class="theme-section-muted space-y-1 text-sm"
            >
              <li
                v-for="issue in record.status.issues"
                :key="issue"
              >
                {{ issue }}
              </li>
            </ul>
          </section>
        </div>
      </template>
      <section
        v-if="aboutOpen && hasLongDescription"
        class="mx-auto max-w-[70ch] space-y-3 px-1 pb-10 pt-2"
        data-testid="encounter-long-description"
      >
        <h3 class="theme-section-title theme-display text-2xl">
          About this Encounter
        </h3>
        <CardMarkupText
          class="theme-section-title break-words text-base leading-7"
          :markup="record.long_description_markup || record.long_description"
          :hover-mode="hoverSurface.effectiveHoverMode.value"
        />
      </section>
      <section
        v-else
        class="space-y-4"
      >
        <p
          v-if="!activeEntries.length"
          class="theme-section-muted text-sm"
        >
          No cards added to this Encounter yet.
        </p>
        <CardDecklist
          v-else-if="layout === 'list'"
          :entries="sortedEntries"
          :groups="groupedEntries"
          :group-by-type="groupByType && activeBoard !== 'boss'"
          :hover-mode="hoverSurface.effectiveHoverMode.value"
          :navigation-target="cardLocation"
        />
        <CardCollectionGrid
          v-else
          :entries="sortedEntries"
          :groups="groupedEntries"
          :group-by-type="groupByType && activeBoard !== 'boss'"
          :grid-style="gridStyle"
          :card-style="cardStyle"
          :card-height-rem="cardHeightRem"
          :hover-mode="hoverSurface.effectiveHoverMode.value"
          :navigation-target="cardLocation"
        />
      </section>
    </CollectionDetailLayout>
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useLocalStorage } from '@vueuse/core';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { Pencil, Trash2 } from 'lucide-vue-next';
import { fetchEncounter, deleteEncounter, exportEncounter } from '@/domain/encounters/api';
import type { EncounterRecord } from '@/domain/encounters/types';
import type { CardFiltersResponse } from '@/domain/cards/types';
import { fetchCardFilters } from '@/domain/cards/api';
import { useAuthStore } from '@/domain/session/store';
import { cardFactionLabel } from '@/domain/cards/cardFactions';
import { copyTtsExport } from '@/domain/cards/utils/copyTtsExport';
import { useCardCollectionGrid } from '@/domain/cards/composables/useCardCollectionGrid';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import { useCardCollectionLayout } from '@/domain/cards/composables/useCardCollectionLayout';
import CardCollectionGrid from '@/domain/cards/components/CardCollectionGrid.vue';
import CardCollectionLayoutToggle from '@/domain/cards/components/CardCollectionLayoutToggle.vue';
import CardDecklist from '@/domain/cards/components/CardDecklist.vue';
import CardCollectionViewOptions from '@/domain/cards/components/CardCollectionViewOptions.vue';
import CardCollectionDetailLoadingSkeleton from '@/domain/cards/components/CardCollectionDetailLoadingSkeleton.vue';
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import CollectionDetailLayout from '@/shared/components/CollectionDetailLayout.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import ExtraActionsMenu from '@/shared/components/app/ExtraActionsMenu.vue';
import AppBoardTabs, { type AppBoardTab } from '@/shared/components/app/AppBoardTabs.vue';
import TtsCopyIcon from '@/shared/components/icons/TtsCopyIcon.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';
import { getApiErrorMessage } from '@/shared/api/errors';
import { toAbsoluteApiUrl } from '@/shared/api/client';
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const record = ref<EncounterRecord | null>(null);
const loading = ref(true);
const error = ref('');
const exporting = ref(false);
const activeBoard = ref('mainboard');
const countBoardCards = (entries: { quantity: number }[]): number =>
  entries.reduce((sum, entry) => sum + entry.quantity, 0);
const ABOUT_VIEW = 'about';
// About replaces the card area with the long description; boards bring the cards back as they were.
const aboutOpen = ref(false);
const hasLongDescription = computed(() =>
  Boolean(record.value?.long_description_markup || record.value?.long_description),
);
const activeView = computed({
  get: () => (aboutOpen.value ? ABOUT_VIEW : activeBoard.value),
  set: (view: string) => {
    aboutOpen.value = view === ABOUT_VIEW;
    if (view !== ABOUT_VIEW) activeBoard.value = view;
  },
});
const boardTabs = computed<AppBoardTab[]>(() => {
  if (!record.value) return [];
  const tabs: AppBoardTab[] = [
    ...(hasLongDescription.value ? [{ id: ABOUT_VIEW, label: 'About' }] : []),
    {
      id: 'mainboard',
      label: 'Mainboard',
      count: record.value.total_cards,
      detail: `${record.value.total_cards} cards, ${record.value.entries.length} unique`,
    },
    ...record.value.sideboards.map((board) => ({
      id: board.id,
      label: board.name,
      count: countBoardCards(board.entries),
      detail: `${countBoardCards(board.entries)} cards, ${board.entries.length} unique`,
    })),
  ];
  // The aside already shows a single boss; the tab only earns its place for a multi-card boss group.
  if (record.value.boss_cards.length > 1) {
    tabs.push({ id: 'boss', label: 'Boss', count: record.value.boss_cards.length });
  }
  return tabs;
});
const activeSideboard = computed(() =>
  record.value?.sideboards.find((board) => board.id === activeBoard.value),
);
const library = computed(() =>
  route.query.return_to === 'staff_encounters' && auth.canAccessStaffRoutes
    ? 'staff'
    : route.query.return_to === 'my_encounters' && auth.authenticated
      ? 'mine'
      : 'public',
);
const backLink = computed(() => ({
  path:
    library.value === 'staff'
      ? '/staff/encounters'
      : library.value === 'mine'
        ? '/my/encounters'
        : '/encounters',
  query: { q: route.query.q, factions: route.query.factions, is_official: route.query.is_official },
}));
const cardLocation = (cardId: string) => ({
  path: `/cards/${cardId}`,
  query: {
    return_to: 'encounter',
    encounter_id: String(route.params.id),
    encounter_library: library.value,
    q: route.query.q,
    factions: route.query.factions,
    is_official: route.query.is_official,
  },
});
const types = ref<CardFiltersResponse['types']>([]);
const sortSurface = useCardSortSurface('deckDetail');
const hoverSurface = useHoverModeSurface('deckDetail');
const { cardScale } = useGalleryOptions();
const { layout } = useCardCollectionLayout();
const bossImageUrl = computed(() =>
  record.value?.boss_card?.image_url ? toAbsoluteApiUrl(record.value.boss_card.image_url) : null,
);
const groupByType = useLocalStorage('card-reader.encounter-detail-group-by-type', true);
const activeEntries = computed(() =>
  !record.value
    ? []
    : activeBoard.value === 'boss'
      ? record.value.boss_cards.map((card) => ({ card, quantity: 1 }))
      : (activeSideboard.value?.entries ?? record.value.entries),
);
const { cardHeightRem, cardStyle, gridStyle, sortedEntries, groupedEntries } =
  useCardCollectionGrid(activeEntries, types, 'evil', sortSurface.effectiveSort, cardScale);
let generation = 0;
const load = async () => {
  const current = ++generation;
  record.value = null;
  loading.value = true;
  error.value = '';
  exporting.value = false;
  activeBoard.value = 'mainboard';
  aboutOpen.value = false;
  try {
    const [value, filters] = await Promise.all([
      fetchEncounter(String(route.params.id), false),
      fetchCardFilters('evil').catch(() => null),
    ]);
    if (current !== generation) return;
    record.value = value;
    types.value = filters?.types ?? [];
  } catch (cause) {
    if (current === generation)
      error.value = getApiErrorMessage(cause, 'Encounter not found or unavailable.');
  } finally {
    if (current === generation) loading.value = false;
  }
};
const copyExport = async () => {
  if (!record.value || exporting.value) return;
  const current = generation;
  const sideboardId = activeSideboard.value?.id;
  exporting.value = true;
  error.value = '';
  try {
    const result = await exportEncounter(record.value.id, sideboardId);
    if (current !== generation) return;
    await copyTtsExport(
      result,
      sideboardId ? 'TTS sideboard copied to clipboard' : 'TTS Encounter copied to clipboard',
    );
  } catch (cause) {
    if (current === generation) error.value = getApiErrorMessage(cause, 'Export failed.');
  } finally {
    if (current === generation) exporting.value = false;
  }
};
const remove = async () => {
  const selected = record.value;
  if (!selected || !window.confirm(`Delete ${selected.name || 'this Encounter'}?`)) return;
  try {
    await deleteEncounter(selected.id, selected.revision);
    await router.push(backLink.value);
  } catch (cause) {
    error.value = getApiErrorMessage(
      cause,
      'Could not delete Encounter. Reload before trying again.',
    );
  }
};

watch(
  () => [route.params.id, auth.user?.id, auth.canAccessStaffRoutes],
  () => {
    void load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  generation++;
});
</script>
