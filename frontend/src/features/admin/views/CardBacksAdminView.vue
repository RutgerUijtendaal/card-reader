<template>
  <div class="page-card space-y-6">
    <section aria-labelledby="card-back-defaults-heading">
      <div class="theme-divider flex flex-wrap items-end justify-between gap-3 border-b pb-4">
        <div>
          <h3
            id="card-back-defaults-heading"
            class="theme-section-title text-base font-semibold"
          >
            Pool defaults
          </h3>
          <p class="theme-section-muted mt-1 text-sm">
            Cards without an override inherit the default for their pool.
          </p>
        </div>
        <p class="theme-section-muted text-xs">
          Defaults can share the same asset.
        </p>
      </div>

      <div
        v-if="initialLoading"
        class="mt-4 grid gap-3 lg:grid-cols-3"
        aria-label="Loading pool defaults"
      >
        <div
          v-for="option in CARD_POOL_OPTIONS"
          :key="option.value"
          class="theme-card-frame-muted animate-pulse rounded-xl p-4"
        >
          <div class="h-4 w-20 rounded bg-[var(--color-surface-soft)]" />
          <div class="mt-4 grid grid-cols-[minmax(0,1fr)_5rem] gap-3">
            <div class="h-10 rounded-lg bg-[var(--color-surface-soft)]" />
            <div class="aspect-[63/88] rounded-lg bg-[var(--color-surface-soft)]" />
          </div>
        </div>
      </div>

      <div
        v-else
        class="mt-4 grid gap-3 lg:grid-cols-3"
      >
        <article
          v-for="option in CARD_POOL_OPTIONS"
          :key="option.value"
          class="theme-card-frame-muted rounded-xl p-4"
        >
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <h4 class="theme-section-title text-sm font-semibold">
                {{ option.label }}
              </h4>
              <p class="theme-section-muted mt-0.5 text-xs">
                Default card back
              </p>
            </div>
            <span
              class="theme-pill px-2 py-0.5 text-xs"
              :class="defaults[option.value] ? 'theme-pill-success' : 'theme-pill-neutral'"
            >
              {{ defaults[option.value] ? 'Set' : 'Missing' }}
            </span>
          </div>
          <CardBackSelect
            :model-value="defaults[option.value]?.id ?? null"
            :card-pool="option.value"
            :assets="cardBacks"
            :defaults="defaults"
            :disabled="loading || settingPool !== null"
            :aria-label="`${option.label} default card back`"
            selection-kind="default"
            @update:model-value="setDefault(option.value, $event)"
          />
        </article>
      </div>
    </section>

    <section aria-labelledby="card-back-library-heading">
      <div class="theme-divider flex flex-wrap items-end justify-between gap-4 border-b pb-4">
        <div>
          <h3
            id="card-back-library-heading"
            class="theme-section-title text-base font-semibold"
          >
            Card-back library
          </h3>
          <p
            class="theme-section-muted mt-1 text-sm"
            aria-live="polite"
          >
            {{ librarySummary }}
          </p>
        </div>
        <div class="flex w-full flex-wrap gap-2 sm:w-auto">
          <input
            v-model="searchQuery"
            class="input-base min-w-48 flex-1 sm:w-56 sm:flex-none"
            placeholder="Filter card backs"
            aria-label="Filter card backs"
          >
          <button
            class="btn-secondary inline-flex items-center gap-2"
            type="button"
            :disabled="loading"
            @click="loadCardBackData"
          >
            <RefreshCw
              class="h-4 w-4"
              :class="{ 'animate-spin': loading && hasLoaded }"
            />
            Refresh
          </button>
          <button
            class="btn-primary inline-flex items-center gap-2"
            type="button"
            @click="openUploadModal"
          >
            <Plus class="h-4 w-4" />
            Add card back
          </button>
        </div>
      </div>

      <p
        v-if="errorMessage"
        class="theme-alert-danger mt-4"
        role="alert"
      >
        {{ errorMessage }}
      </p>

      <div
        v-if="initialLoading"
        class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6"
        aria-label="Loading card-back library"
      >
        <div
          v-for="index in 6"
          :key="index"
          class="theme-card-frame-muted animate-pulse rounded-xl p-3"
        >
          <div class="aspect-[63/88] rounded-lg bg-[var(--color-surface-soft)]" />
          <div class="mt-3 h-4 w-2/3 rounded bg-[var(--color-surface-soft)]" />
          <div class="mt-2 h-3 w-1/2 rounded bg-[var(--color-surface-soft)]" />
        </div>
      </div>

      <div
        v-else-if="filteredCardBacks.length === 0"
        class="theme-empty-state mt-4 rounded-xl p-10 text-center text-sm"
      >
        <h4 class="theme-section-title font-semibold">
          {{ cardBacks.length === 0 ? 'No card backs yet' : 'No matching card backs' }}
        </h4>
        <p class="theme-section-muted mx-auto mt-1 max-w-md">
          {{ cardBacks.length === 0
            ? 'Add the first image to start the reusable card-back library.'
            : 'Try a different label.' }}
        </p>
        <button
          v-if="cardBacks.length === 0"
          class="btn-primary mt-4 inline-flex items-center gap-2"
          type="button"
          @click="openUploadModal"
        >
          <Plus class="h-4 w-4" />
          Add card back
        </button>
      </div>

      <div
        v-else
        class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6"
        role="list"
        aria-label="Card-back assets"
      >
        <article
          v-for="cardBack in filteredCardBacks"
          :key="cardBack.id"
          class="theme-card-frame rounded-xl p-3"
          role="listitem"
        >
          <div class="theme-card-image-well aspect-[63/88] overflow-hidden rounded-lg">
            <img
              v-if="cardBack.image_url"
              class="h-full w-full object-cover"
              :src="toAbsoluteApiUrl(cardBack.image_url)"
              :alt="cardBack.label"
              loading="lazy"
            >
            <div
              v-else
              class="theme-section-muted flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-xs"
            >
              <ImageOff class="h-6 w-6" />
              Image unavailable
            </div>
          </div>

          <div class="mt-3 min-w-0">
            <div class="flex items-start justify-between gap-2">
              <h4 class="theme-section-title min-w-0 truncate text-sm font-semibold">
                {{ cardBack.label }}
              </h4>
              <span
                v-if="!cardBack.is_usable"
                class="theme-pill theme-pill-danger shrink-0 px-2 py-0.5 text-[11px]"
              >
                Missing
              </span>
            </div>
            <div class="mt-3 flex min-h-6 flex-wrap gap-1.5">
              <span
                v-for="pool in cardBack.default_for_pools"
                :key="pool"
                class="theme-pill theme-pill-success px-2 py-0.5 text-[11px]"
              >
                {{ poolLabel(pool) }} default
              </span>
              <span
                v-if="cardBack.default_for_pools.length === 0"
                class="theme-section-muted text-[11px]"
              >
                Not a pool default
              </span>
            </div>

            <div class="theme-divider theme-section-muted mt-3 border-t pt-3 text-[11px]">
              {{ cardBack.override_card_count }} card override{{ cardBack.override_card_count === 1 ? '' : 's' }}
            </div>
          </div>
        </article>
      </div>
    </section>

    <CardBackUploadModal
      :open="uploadModalOpen"
      :uploading="uploading"
      :error-message="uploadErrorMessage"
      @close="closeUploadModal"
      @submit="uploadSelectedCardBack"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ImageOff, Plus, RefreshCw } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { getApiErrorMessageWithCause as extractErrorMessage } from '@/shared/api/errors';
import CardBackSelect from '@/domain/card-backs/components/CardBackSelect.vue';
import {
  fetchCardBackDefaults,
  fetchCardBacks,
  setPoolCardBackDefault,
  uploadCardBack,
} from '@/domain/card-backs/api';
import type { CardBackDefaults, CardBackRecord } from '@/domain/card-backs/types';
import { CARD_POOL_OPTIONS, type CardPool } from '@/domain/cards/cardPools';
import CardBackUploadModal from '@/features/admin/components/CardBackUploadModal.vue';

const emptyDefaults = (): CardBackDefaults => ({ player: null, evil: null, neutral: null });
const cardBacks = ref<CardBackRecord[]>([]);
const defaults = ref<CardBackDefaults>(emptyDefaults());
const loading = ref(false);
const hasLoaded = ref(false);
const uploading = ref(false);
const uploadModalOpen = ref(false);
const settingPool = ref<CardPool | null>(null);
const searchQuery = ref('');
const errorMessage = ref('');
const uploadErrorMessage = ref('');

const initialLoading = computed(() => loading.value && !hasLoaded.value);
const filteredCardBacks = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase();
  if (!query) return cardBacks.value;
  return cardBacks.value.filter((asset) => asset.label.toLocaleLowerCase().includes(query));
});
const librarySummary = computed(() => {
  const total = cardBacks.value.length;
  const noun = total === 1 ? 'card back' : 'card backs';
  if (searchQuery.value.trim()) {
    return `${filteredCardBacks.value.length} of ${total} ${noun}`;
  }
  return `${total} ${noun}`;
});

const loadCardBackData = async (): Promise<void> => {
  loading.value = true;
  errorMessage.value = '';
  try {
    [cardBacks.value, defaults.value] = await Promise.all([fetchCardBacks(), fetchCardBackDefaults()]);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Card backs could not be loaded.');
  } finally {
    loading.value = false;
    hasLoaded.value = true;
  }
};

const openUploadModal = (): void => {
  uploadErrorMessage.value = '';
  uploadModalOpen.value = true;
};

const closeUploadModal = (): void => {
  if (uploading.value) return;
  uploadModalOpen.value = false;
  uploadErrorMessage.value = '';
};

const uploadSelectedCardBack = async (payload: { file: File; label: string }): Promise<void> => {
  if (uploading.value) return;
  uploading.value = true;
  uploadErrorMessage.value = '';
  try {
    await uploadCardBack(payload.file, payload.label);
  } catch (error) {
    uploadErrorMessage.value = extractErrorMessage(error, 'Card back could not be uploaded.');
    toast.error(uploadErrorMessage.value);
    return;
  } finally {
    uploading.value = false;
  }
  uploadModalOpen.value = false;
  toast.success('Card-back asset uploaded.');
  await loadCardBackData();
};

const setDefault = async (cardPool: CardPool, cardBackId: string | null): Promise<void> => {
  if (settingPool.value !== null || (defaults.value[cardPool]?.id ?? null) === cardBackId) return;
  settingPool.value = cardPool;
  errorMessage.value = '';
  try {
    await setPoolCardBackDefault(cardPool, cardBackId);
    await loadCardBackData();
    toast.success(`${poolLabel(cardPool)} default updated.`);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Pool default could not be updated.');
    toast.error(errorMessage.value);
  } finally {
    settingPool.value = null;
  }
};

const poolLabel = (cardPool: CardPool): string =>
  CARD_POOL_OPTIONS.find((option) => option.value === cardPool)?.label ?? cardPool;

onMounted(() => { void loadCardBackData(); });
</script>
