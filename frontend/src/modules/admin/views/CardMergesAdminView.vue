<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <div class="space-y-1">
      <h3 class="theme-section-title text-base font-semibold">
        Card Merges
      </h3>
      <p class="theme-section-muted text-sm">
        Merge renamed duplicate cards into one canonical card while preserving aliases and version history.
      </p>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div class="app-scrollbar min-h-0 space-y-4 overflow-y-auto pr-1">
        <section class="theme-muted-panel p-4">
          <div class="grid gap-4 lg:grid-cols-2">
            <div class="space-y-3">
              <div>
                <h4 class="theme-section-title text-sm font-semibold">
                  Target Card
                </h4>
                <p class="theme-section-muted text-xs">
                  The card that keeps the canonical identity and latest version.
                </p>
              </div>
              <label class="field-label">
                Search target
                <input
                  v-model="targetSearch"
                  class="input-base"
                  placeholder="Search card name"
                  @keyup.enter="searchTargets"
                >
              </label>
              <button
                class="btn-secondary"
                type="button"
                :disabled="searchingTargets"
                @click="searchTargets"
              >
                {{ searchingTargets ? 'Searching...' : 'Search Target' }}
              </button>
              <div class="grid gap-2">
                <button
                  v-for="card in targetResults"
                  :key="`target-${card.id}`"
                  class="theme-card-frame-muted rounded-xl px-3 py-2 text-left"
                  type="button"
                  @click="selectTarget(card)"
                >
                  <span class="theme-section-title block text-sm font-semibold">{{ card.name }}</span>
                  <span class="theme-section-muted text-xs">{{ card.id }}</span>
                </button>
              </div>
            </div>

            <div class="space-y-3">
              <div>
                <h4 class="theme-section-title text-sm font-semibold">
                  Source Cards
                </h4>
                <p class="theme-section-muted text-xs">
                  These duplicate cards will be folded into the target history.
                </p>
              </div>
              <label class="field-label">
                Search source
                <input
                  v-model="sourceSearch"
                  class="input-base"
                  placeholder="Search old card name"
                  @keyup.enter="searchSources"
                >
              </label>
              <button
                class="btn-secondary"
                type="button"
                :disabled="searchingSources"
                @click="searchSources"
              >
                {{ searchingSources ? 'Searching...' : 'Search Sources' }}
              </button>
              <div class="grid gap-2">
                <button
                  v-for="card in sourceResults"
                  :key="`source-${card.id}`"
                  class="theme-card-frame-muted rounded-xl px-3 py-2 text-left"
                  type="button"
                  :disabled="card.id === targetCard?.id || sourceCards.some((source) => source.id === card.id)"
                  @click="addSource(card)"
                >
                  <span class="theme-section-title block text-sm font-semibold">{{ card.name }}</span>
                  <span class="theme-section-muted text-xs">{{ card.id }}</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section class="theme-muted-panel p-4">
          <div class="grid gap-4 lg:grid-cols-2">
            <div>
              <h4 class="theme-section-title text-sm font-semibold">
                Selected Target
              </h4>
              <div
                v-if="targetCard"
                class="theme-card-frame-muted mt-3 rounded-xl px-3 py-2"
              >
                <p class="theme-section-title text-sm font-semibold">
                  {{ targetCard.name }}
                </p>
                <p class="theme-section-muted text-xs">
                  {{ targetCard.id }}
                </p>
              </div>
              <p
                v-else
                class="theme-empty-state mt-3"
              >
                No target selected.
              </p>
            </div>
            <div>
              <h4 class="theme-section-title text-sm font-semibold">
                Selected Sources
              </h4>
              <div v-if="sourceCards.length" class="mt-3 grid gap-2">
                <div
                  v-for="card in sourceCards"
                  :key="`selected-source-${card.id}`"
                  class="theme-card-frame-muted flex items-center justify-between gap-3 rounded-xl px-3 py-2"
                >
                  <div>
                    <p class="theme-section-title text-sm font-semibold">
                      {{ card.name }}
                    </p>
                    <p class="theme-section-muted text-xs">
                      {{ card.id }}
                    </p>
                  </div>
                  <button
                    class="btn-secondary h-8"
                    type="button"
                    @click="removeSource(card.id)"
                  >
                    Remove
                  </button>
                </div>
              </div>
              <p
                v-if="sourceCards.length === 0"
                class="theme-empty-state mt-3"
              >
                No source cards selected.
              </p>
            </div>
          </div>
        </section>
      </div>

      <aside class="theme-muted-panel app-scrollbar min-h-0 overflow-y-auto p-4">
        <div class="flex flex-wrap gap-3">
          <button
            class="btn-secondary"
            type="button"
            :disabled="!canPreview || previewing"
            @click="previewMerge"
          >
            {{ previewing ? 'Previewing...' : 'Preview Merge' }}
          </button>
          <button
            class="btn-primary"
            type="button"
            :disabled="!preview?.can_apply || applying"
            @click="applyMerge"
          >
            {{ applying ? 'Applying...' : 'Apply Merge' }}
          </button>
        </div>

        <div
          v-if="preview"
          class="mt-4 space-y-4"
        >
          <div>
            <h4 class="theme-section-title text-sm font-semibold">
              Preview
            </h4>
            <p class="theme-section-muted mt-1 text-sm">
              Resulting history: {{ preview.resulting_version_count }} versions.
            </p>
          </div>

          <div class="theme-card-frame-muted rounded-xl p-3 text-sm">
            <p>Deck collisions: {{ preview.relations.deck_entry_collisions }}</p>
            <p>Sideboard collisions: {{ preview.relations.sideboard_entry_collisions }}</p>
            <p>Group collisions: {{ preview.relations.group_member_collisions }}</p>
            <p>Hero references: {{ preview.relations.hero_references }}</p>
            <p>Anchored groups: {{ preview.relations.anchored_groups }}</p>
          </div>

          <div>
            <h5 class="theme-section-title text-xs font-semibold uppercase tracking-wide">
              Aliases
            </h5>
            <div class="mt-2 flex flex-wrap gap-2">
              <span
                v-for="alias in preview.aliases"
                :key="alias.key"
                class="theme-pill px-2 py-1 text-xs"
                :class="alias.conflict_card_id ? 'theme-pill-warning' : 'theme-pill-neutral'"
              >
                {{ alias.key }}
              </span>
            </div>
          </div>

          <div
            v-if="preview.blocking_conflicts.length > 0"
            class="theme-card-frame-muted rounded-xl border border-amber-400/40 p-3"
          >
            <h5 class="theme-section-title text-sm font-semibold">
              Blocking Conflicts
            </h5>
            <p
              v-for="conflict in preview.blocking_conflicts"
              :key="conflict"
              class="theme-section-muted mt-2 text-sm"
            >
              {{ conflict }}
            </p>
          </div>
        </div>

        <p
          v-else
          class="theme-section-muted mt-4 text-sm"
        >
          Select a target and at least one source card, then preview before applying.
        </p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { api } from '@/api/client';
import { parseAdminMergeTargetId } from '@/modules/admin/adminRouteState';
import type { CardMergeApplyResponse, CardMergePreview } from '@/modules/admin/types';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';

const { route } = useAdminRouteSync();
const targetSearch = ref('');
const sourceSearch = ref('');
const targetResults = ref<CardListItem[]>([]);
const sourceResults = ref<CardListItem[]>([]);
const targetCard = ref<CardListItem | null>(null);
const sourceCards = ref<CardListItem[]>([]);
const preview = ref<CardMergePreview | null>(null);
const searchingTargets = ref(false);
const searchingSources = ref(false);
const previewing = ref(false);
const applying = ref(false);

const canPreview = computed(() => targetCard.value !== null && sourceCards.value.length > 0);

const searchCards = async (query: string): Promise<CardListItem[]> => {
  const response = await api.get<PaginatedCardsResponse<CardListItem>>('/cards', {
    params: { q: query, page: 1, page_size: 8 },
  });
  return response.data.results.filter((item): item is CardListItem => item.result_type === 'card');
};

const searchTargets = async (): Promise<void> => {
  searchingTargets.value = true;
  try {
    targetResults.value = await searchCards(targetSearch.value);
  } finally {
    searchingTargets.value = false;
  }
};

const searchSources = async (): Promise<void> => {
  searchingSources.value = true;
  try {
    sourceResults.value = await searchCards(sourceSearch.value);
  } finally {
    searchingSources.value = false;
  }
};

const selectTarget = (card: CardListItem): void => {
  targetCard.value = card;
  sourceCards.value = sourceCards.value.filter((source) => source.id !== card.id);
  preview.value = null;
};

const addSource = (card: CardListItem): void => {
  if (targetCard.value?.id === card.id || sourceCards.value.some((source) => source.id === card.id)) {
    return;
  }
  sourceCards.value = [...sourceCards.value, card];
  preview.value = null;
};

const removeSource = (cardId: string): void => {
  sourceCards.value = sourceCards.value.filter((source) => source.id !== cardId);
  preview.value = null;
};

const previewMerge = async (): Promise<void> => {
  if (!targetCard.value || sourceCards.value.length === 0) return;
  previewing.value = true;
  try {
    const response = await api.post<CardMergePreview>('/admin/card-merges/preview', {
      target_card_id: targetCard.value.id,
      source_card_ids: sourceCards.value.map((card) => card.id),
    });
    preview.value = response.data;
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to preview card merge.'));
  } finally {
    previewing.value = false;
  }
};

const applyMerge = async (): Promise<void> => {
  if (!targetCard.value || sourceCards.value.length === 0 || !preview.value?.can_apply) return;
  applying.value = true;
  try {
    const response = await api.post<CardMergeApplyResponse>('/admin/card-merges/apply', {
      target_card_id: targetCard.value.id,
      source_card_ids: sourceCards.value.map((card) => card.id),
    });
    toast.success(response.data.message);
    preview.value = response.data.preview;
    sourceCards.value = [];
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to apply card merge.'));
  } finally {
    applying.value = false;
  }
};

const loadPrefilledTarget = async (): Promise<void> => {
  const targetId = parseAdminMergeTargetId(route.query);
  if (!targetId || targetCard.value?.id === targetId) return;
  try {
    const response = await api.get<CardListItem>(`/cards/${targetId}`);
    targetCard.value = response.data;
    targetSearch.value = response.data.name;
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to load preselected merge target.'));
  }
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  return fallback;
};

onMounted(loadPrefilledTarget);
watch(() => route.query, loadPrefilledTarget);
</script>
