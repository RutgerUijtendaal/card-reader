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
      subtitle-class="!mt-4 text-sm"
    >
      <template
        v-if="record"
        #subtitle
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
    <CollectionDetailLayout
      v-if="record"
      :expanded="detailsExpanded"
      details-id="encounter-detail-panel"
    >
      <template #aside>
        <div class="space-y-4">
          <h3 class="theme-section-title text-base font-semibold">
            Boss
          </h3>
          <div class="space-y-3">
            <div
              class="theme-card-frame theme-card-image-well mx-auto aspect-[63/88] w-full max-w-[22rem] overflow-hidden rounded-2xl"
            >
              <img
                v-if="record.boss_card?.image_url"
                :src="toAbsoluteApiUrl(record.boss_card.image_url)"
                :alt="record.boss_card.name"
                class="h-full w-full object-cover"
              >
              <div
                v-else
                class="theme-kicker flex h-full items-center justify-center text-xs"
              >
                {{ record.boss_card ? 'No image' : 'No boss selected' }}
              </div>
            </div>
            <p class="theme-section-title text-lg font-semibold">
              {{ record.boss_card?.name || 'No boss selected' }}
            </p>
            <p class="theme-section-muted text-sm">
              By <span class="theme-section-title font-medium">{{ record.creator.username }}</span>
            </p>
          </div>
          <section
            class="theme-divider space-y-2 border-t pt-4"
            data-testid="encounter-summary"
          >
            <div class="flex items-center justify-between gap-3">
              <h4 class="theme-section-title text-sm font-semibold">
                Summary
              </h4>
              <button
                v-if="record.long_description_markup || record.long_description"
                class="theme-ghost-button inline-flex items-center gap-1 text-xs font-medium"
                type="button"
                :aria-expanded="detailsExpanded"
                aria-controls="encounter-detail-panel"
                @click="detailsExpanded = !detailsExpanded"
              >
                Details<ChevronRight
                  class="h-3.5 w-3.5"
                  :class="detailsExpanded ? 'rotate-90' : ''"
                />
              </button>
            </div>
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
      <template #aside-footer>
        <CardCollectionViewOptions
          v-model:card-scale="cardScale"
          v-model:group-by-type="groupByType"
          :sort-surface="sortSurface"
          :hover-surface="hoverSurface"
        />
      </template>
      <template #details>
        <section
          class="space-y-2"
          data-testid="encounter-long-description"
        >
          <h3 class="theme-section-title text-base font-semibold">
            About this Encounter
          </h3>
          <CardMarkupText
            class="theme-section-muted break-words text-sm"
            :markup="record.long_description_markup || record.long_description"
            :hover-mode="hoverSurface.effectiveHoverMode.value"
          />
        </section>
      </template>
      <template #details-footer>
        <button
          class="theme-ghost-button flex w-full items-center justify-center gap-2 px-3 py-2 text-sm font-semibold"
          type="button"
          @click="detailsExpanded = false"
        >
          <X class="h-4 w-4" />Close details
        </button>
      </template>
      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="theme-pill text-xs"
              :class="activeBoard === 'mainboard' ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoard = 'mainboard'"
            >
              Mainboard
              <span class="ml-1 opacity-80">{{ record.total_cards }} / {{ record.entries.length }}</span>
            </button>
            <button
              v-for="board in record.sideboards"
              :key="board.id"
              class="theme-pill text-xs"
              :class="activeBoard === board.id ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoard = board.id"
            >
              {{ board.name }}
              <span class="ml-1 opacity-80">{{ board.entries.reduce((sum, entry) => sum + entry.quantity, 0) }} /
                {{ board.entries.length }}</span>
            </button>
            <button
              v-if="record.boss_cards.length"
              class="theme-pill text-xs"
              :class="activeBoard === 'boss' ? 'theme-pill-accent' : 'theme-pill-neutral'"
              type="button"
              @click="activeBoard = 'boss'"
            >
              Boss <span class="ml-1 opacity-80">{{ record.boss_cards.length }}</span>
            </button>
          </div>
          <span class="theme-pill theme-pill-neutral text-xs">{{ record.total_cards + record.boss_cards.length }} total including boss</span>
        </div>
        <p
          v-if="!activeEntries.length"
          class="theme-section-muted text-sm"
        >
          No cards added to this Encounter yet.
        </p>
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
        <div
          v-if="exportText"
          class="space-y-2"
        >
          <label class="field-label">TTS import code<textarea
            :value="exportText"
            readonly
            class="input-base h-24"
            @focus="($event.target as HTMLTextAreaElement).select()"
          />
          </label>
          <p class="theme-section-muted text-sm">
            {{ exportMessage }}
          </p>
        </div>
      </section>
    </CollectionDetailLayout>
  </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useLocalStorage, useMediaQuery } from '@vueuse/core';
import { useRoute, useRouter } from 'vue-router';
import { ChevronRight, Pencil, Trash2, X } from 'lucide-vue-next';
import { fetchEncounter, deleteEncounter, exportEncounter } from '@/domain/encounters/api';
import type { EncounterRecord } from '@/domain/encounters/types';
import type { CardFiltersResponse } from '@/domain/cards/types';
import { fetchCardFilters } from '@/domain/cards/api';
import { useAuthStore } from '@/domain/session/store';
import { cardFactionLabel } from '@/domain/cards/cardFactions';
import { ttsExportSheetDescription } from '@/domain/cards/utils/ttsExportResponse';
import { copyTtsExport } from '@/domain/cards/utils/copyTtsExport';
import { useCardCollectionGrid } from '@/domain/cards/composables/useCardCollectionGrid';
import { useCardSortSurface } from '@/domain/cards/composables/useCardSortPreferences';
import { useHoverModeSurface } from '@/domain/cards/composables/useHoverModePreferences';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import CardCollectionGrid from '@/domain/cards/components/CardCollectionGrid.vue';
import CardCollectionViewOptions from '@/domain/cards/components/CardCollectionViewOptions.vue';
import CardCollectionDetailLoadingSkeleton from '@/domain/cards/components/CardCollectionDetailLoadingSkeleton.vue';
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import CollectionDetailLayout from '@/shared/components/CollectionDetailLayout.vue';
import AppPageHeader from '@/shared/components/app/AppPageHeader.vue';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';
import ExtraActionsMenu from '@/shared/components/app/ExtraActionsMenu.vue';
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
const exportText = ref('');
const exportMessage = ref('');
const detailsExpanded = ref(false);
const canAutoExpand = useMediaQuery('(min-width: 1536px)');
const activeBoard = ref('mainboard');
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
  exportText.value = '';
  exporting.value = false;
  activeBoard.value = 'mainboard';
  detailsExpanded.value = false;
  try {
    const [value, filters] = await Promise.all([
      fetchEncounter(String(route.params.id), false),
      fetchCardFilters('evil').catch(() => null),
    ]);
    if (current !== generation) return;
    record.value = value;
    types.value = filters?.types ?? [];
    detailsExpanded.value = Boolean(
      (value.long_description_markup || value.long_description) && canAutoExpand.value,
    );
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
    exportText.value = result.encodedPayload;
    exportMessage.value = `${result.exportedCount} cards. ${ttsExportSheetDescription(result)}`;
    try {
      await copyTtsExport(
        result,
        sideboardId ? 'TTS sideboard copied to clipboard' : 'TTS Encounter copied to clipboard',
      );
      exportMessage.value = `Copied to clipboard. ${exportMessage.value}`;
    } catch {
      /* The import code remains selectable. */
    }
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
