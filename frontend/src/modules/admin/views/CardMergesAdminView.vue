<template>
  <div class="page-card flex min-h-0 flex-col space-y-4 xl:h-[calc(100vh-10rem)]">
    <div class="space-y-1">
      <h3 class="theme-section-title text-base font-semibold">
        Card Merges
      </h3>
      <p class="theme-section-muted text-sm">
        Merge one duplicate card into one canonical card while preserving aliases and version history.
      </p>
    </div>

    <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div class="app-scrollbar grid min-h-0 gap-4 overflow-y-auto pr-1 xl:grid-cols-[minmax(14rem,1fr)_auto_minmax(14rem,1fr)] xl:items-stretch">
        <div class="theme-panel-shell flex min-h-[32rem] flex-col space-y-5 p-4 xl:min-h-0">
          <div class="theme-card-frame-muted rounded-xl p-3">
            <h4 class="theme-section-title text-lg font-semibold">
              Source Card
            </h4>
            <p class="theme-section-muted mt-1 text-sm">
              This duplicate card will be folded into the target history.
            </p>
          </div>

          <div class="mx-auto w-full max-w-[22rem]">
            <CardSearchSelect
              label="Search source"
              placeholder="Search duplicate card"
              :disabled-card-ids="targetCard ? [targetCard.id] : []"
              disabled-action-label="Target"
              @select="selectSource"
            />
          </div>

          <div class="mx-auto w-full max-w-[22rem]">
            <div class="theme-card-frame relative aspect-[63/88] rounded-2xl">
              <template v-if="sourceCard">
                <img
                  v-if="sourceCard.image_url"
                  :src="toAbsoluteApiUrl(sourceCard.image_url)"
                  :alt="sourceCard.name"
                  class="h-full w-full object-contain"
                >
                <CardLoadingSkeleton
                  v-else
                  :animated="false"
                />
                <span
                  v-if="cardIsDeprecated(sourceCard)"
                  class="theme-pill theme-pill-warning absolute left-3 top-3 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide"
                >
                  Deprecated
                </span>
              </template>
              <CardLoadingSkeleton
                v-else
                :animated="false"
              />
            </div>
            <div
              v-if="sourceCard"
              class="mt-3 flex items-center justify-between gap-3"
            >
              <div class="min-w-0">
                <p class="theme-section-title truncate text-sm font-semibold">
                  {{ sourceCard.name }}
                </p>
                <p class="theme-section-muted truncate text-xs">
                  {{ sourceCard.label }}
                </p>
              </div>
              <button
                class="btn-secondary h-8 px-3 text-xs"
                type="button"
                @click="clearSource"
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        <div class="flex min-h-24 items-center justify-center xl:min-h-0">
          <div class="theme-card-frame-muted theme-section-title flex h-14 w-14 items-center justify-center rounded-full">
            <ArrowRight class="h-6 w-6" />
          </div>
        </div>

        <div class="theme-panel-shell flex min-h-[32rem] flex-col space-y-5 p-4 xl:min-h-0">
          <div class="theme-card-frame-muted rounded-xl p-3">
            <h4 class="theme-section-title text-lg font-semibold">
              Target Card
            </h4>
            <p class="theme-section-muted mt-1 text-sm">
              This card keeps the canonical identity and latest version.
            </p>
          </div>

          <div class="mx-auto w-full max-w-[22rem]">
            <CardSearchSelect
              label="Search target"
              placeholder="Search canonical card"
              :disabled-card-ids="sourceCard ? [sourceCard.id] : []"
              disabled-action-label="Source"
              @select="selectTarget"
            />
          </div>

          <div class="mx-auto w-full max-w-[22rem]">
            <div class="theme-card-frame relative aspect-[63/88] rounded-2xl">
              <template v-if="targetCard">
                <img
                  v-if="targetCard.image_url"
                  :src="toAbsoluteApiUrl(targetCard.image_url)"
                  :alt="targetCard.name"
                  class="h-full w-full object-contain"
                >
                <CardLoadingSkeleton
                  v-else
                  :animated="false"
                />
                <span
                  v-if="cardIsDeprecated(targetCard)"
                  class="theme-pill theme-pill-warning absolute left-3 top-3 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide"
                >
                  Deprecated
                </span>
              </template>
              <CardLoadingSkeleton
                v-else
                :animated="false"
              />
            </div>
            <div
              v-if="targetCard"
              class="mt-3 flex items-center justify-between gap-3"
            >
              <div class="min-w-0">
                <p class="theme-section-title truncate text-sm font-semibold">
                  {{ targetCard.name }}
                </p>
                <p class="theme-section-muted truncate text-xs">
                  {{ targetCard.label }}
                </p>
              </div>
              <button
                class="btn-secondary h-8 px-3 text-xs"
                type="button"
                @click="clearTarget"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
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
          Select one source card and one target card, then preview before applying.
        </p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { ArrowRight } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { api, toAbsoluteApiUrl } from '@/api/client';
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';
import CardSearchSelect from '@/components/cards/CardSearchSelect.vue';
import { cardIsDeprecated } from '@/modules/card-filters/cardLifecycle';
import { parseAdminMergeSourceId, parseAdminMergeTargetId } from '@/modules/admin/adminRouteState';
import type { CardMergeApplyResponse, CardMergePreview } from '@/modules/admin/types';
import type { CardListItem } from '@/modules/card-detail/types';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';

const { route } = useAdminRouteSync();
const targetCard = ref<CardListItem | null>(null);
const sourceCard = ref<CardListItem | null>(null);
const preview = ref<CardMergePreview | null>(null);
const previewing = ref(false);
const applying = ref(false);

const canPreview = computed(() => targetCard.value !== null && sourceCard.value !== null);

const selectTarget = (card: CardListItem): void => {
  targetCard.value = card;
  if (sourceCard.value?.id === card.id) {
    sourceCard.value = null;
  }
  preview.value = null;
};

const selectSource = (card: CardListItem): void => {
  sourceCard.value = card;
  if (targetCard.value?.id === card.id) {
    targetCard.value = null;
  }
  preview.value = null;
};

const clearTarget = (): void => {
  targetCard.value = null;
  preview.value = null;
};

const clearSource = (): void => {
  sourceCard.value = null;
  preview.value = null;
};

const previewMerge = async (): Promise<void> => {
  if (!targetCard.value || !sourceCard.value) return;
  previewing.value = true;
  try {
    const response = await api.post<CardMergePreview>('/admin/card-merges/preview', {
      target_card_id: targetCard.value.id,
      source_card_ids: [sourceCard.value.id],
    });
    preview.value = response.data;
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to preview card merge.'));
  } finally {
    previewing.value = false;
  }
};

const applyMerge = async (): Promise<void> => {
  if (!targetCard.value || !sourceCard.value || !preview.value?.can_apply) return;
  applying.value = true;
  try {
    const response = await api.post<CardMergeApplyResponse>('/admin/card-merges/apply', {
      target_card_id: targetCard.value.id,
      source_card_ids: [sourceCard.value.id],
    });
    toast.success(response.data.message);
    preview.value = response.data.preview;
    sourceCard.value = null;
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
    selectTarget(response.data);
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to load preselected merge target.'));
  }
};

const loadPrefilledSource = async (): Promise<void> => {
  const sourceId = parseAdminMergeSourceId(route.query);
  if (!sourceId || sourceCard.value?.id === sourceId) return;
  try {
    const response = await api.get<CardListItem>(`/cards/${sourceId}`);
    selectSource(response.data);
  } catch (error) {
    toast.error(extractErrorMessage(error, 'Failed to load preselected merge source.'));
  }
};

const loadPrefilledCards = async (): Promise<void> => {
  await loadPrefilledTarget();
  await loadPrefilledSource();
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  return fallback;
};

onMounted(loadPrefilledCards);
watch(() => route.query, loadPrefilledCards);
</script>
