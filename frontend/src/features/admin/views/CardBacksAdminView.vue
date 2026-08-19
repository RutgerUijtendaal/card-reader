<template>
  <div class="page-card grid min-h-[34rem] gap-5 xl:h-[calc(100vh-10rem)] xl:grid-cols-[minmax(20rem,26rem)_minmax(0,1fr)]">
    <section class="app-scrollbar min-h-0 space-y-4 overflow-y-auto pr-1">
      <div class="theme-divider border-b pb-4">
        <h3 class="theme-section-title text-base font-semibold">
          Pool defaults
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          Each pool inherits its own default. Changing one does not affect the others.
        </p>
      </div>

      <div
        v-for="option in CARD_POOL_OPTIONS"
        :key="option.value"
        class="theme-muted-panel p-4"
      >
        <div class="mb-3 flex items-center justify-between gap-3">
          <div>
            <h4 class="theme-section-title text-sm font-semibold">
              {{ option.label }}
            </h4>
            <p class="theme-section-muted text-xs">
              Default for cards without an override.
            </p>
          </div>
          <span
            v-if="defaults[option.value]"
            class="theme-pill theme-pill-success px-2 py-0.5 text-xs"
          >Set</span>
          <span
            v-else
            class="theme-pill theme-pill-neutral px-2 py-0.5 text-xs"
          >Missing</span>
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
      </div>

      <form
        class="theme-muted-panel grid gap-3 p-4"
        @submit.prevent="uploadSelectedCardBack"
      >
        <div>
          <h4 class="theme-section-title text-sm font-semibold">
            Add asset
          </h4>
          <p class="theme-section-muted text-xs">
            Uploading does not change a pool default.
          </p>
        </div>
        <label class="field-label">
          Label
          <input
            v-model="uploadLabel"
            class="input-base"
            placeholder="Card back name"
          >
        </label>
        <label class="field-label">
          Image
          <input
            ref="fileInput"
            class="input-base"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff"
            @change="selectUploadFile"
          >
        </label>
        <button
          class="btn-primary justify-center"
          type="submit"
          :disabled="!selectedFile || uploading"
        >
          {{ uploading ? 'Uploading...' : 'Upload asset' }}
        </button>
      </form>
    </section>

    <section class="flex min-h-0 flex-col">
      <div class="theme-divider flex flex-wrap items-end justify-between gap-3 border-b pb-4">
        <div>
          <h3 class="theme-section-title text-base font-semibold">
            Asset library
          </h3>
          <p class="theme-section-muted mt-1 text-sm">
            {{ librarySummary }}
          </p>
        </div>
        <div class="flex gap-2">
          <input
            v-model="searchQuery"
            class="input-base w-52"
            placeholder="Filter card backs"
          >
          <button
            class="btn-secondary"
            type="button"
            :disabled="loading"
            @click="loadCardBackData"
          >
            {{ loading ? 'Refreshing...' : 'Refresh' }}
          </button>
        </div>
      </div>

      <p
        v-if="errorMessage"
        class="theme-alert-danger mt-4"
      >
        {{ errorMessage }}
      </p>
      <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto pt-4">
        <div
          v-if="loading"
          class="theme-section-muted text-sm"
        >
          Loading card backs...
        </div>
        <div
          v-else-if="filteredCardBacks.length === 0"
          class="theme-empty-state rounded-lg p-8 text-center text-sm"
        >
          No matching card backs.
        </div>
        <div
          v-else
          class="grid gap-3"
        >
          <article
            v-for="cardBack in filteredCardBacks"
            :key="cardBack.id"
            class="theme-card-frame grid gap-4 rounded-lg p-3 sm:grid-cols-[5rem_minmax(0,1fr)]"
          >
            <div class="theme-card-image-well aspect-[63/88] overflow-hidden rounded-lg">
              <img
                v-if="cardBack.image_url"
                class="h-full w-full object-cover"
                :src="toAbsoluteApiUrl(cardBack.image_url)"
                :alt="cardBack.label"
              >
              <div
                v-else
                class="theme-section-muted flex h-full items-center justify-center text-xs"
              >
                Missing
              </div>
            </div>
            <div class="min-w-0 space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                <h4 class="theme-section-title truncate text-sm font-semibold">
                  {{ cardBack.label }}
                </h4>
                <span
                  v-for="pool in cardBack.default_for_pools"
                  :key="pool"
                  class="theme-pill theme-pill-success px-2 py-0.5 text-xs"
                >{{ poolLabel(pool) }}</span>
                <span
                  v-if="!cardBack.is_usable"
                  class="theme-pill theme-pill-danger px-2 py-0.5 text-xs"
                >Missing image</span>
              </div>
              <p class="theme-section-muted truncate text-xs">
                {{ cardBack.original_filename }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ cardBack.width }} x {{ cardBack.height }} · {{ formatDate(cardBack.created_at) }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ cardBack.override_card_count }} card override{{ cardBack.override_card_count === 1 ? '' : 's' }}
              </p>
            </div>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
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

const emptyDefaults = (): CardBackDefaults => ({ player: null, evil: null, neutral: null });
const cardBacks = ref<CardBackRecord[]>([]);
const defaults = ref<CardBackDefaults>(emptyDefaults());
const loading = ref(false);
const uploading = ref(false);
const settingPool = ref<CardPool | null>(null);
const selectedFile = ref<File | null>(null);
const uploadLabel = ref('');
const searchQuery = ref('');
const errorMessage = ref('');
const fileInput = ref<HTMLInputElement | null>(null);

const filteredCardBacks = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase();
  if (!query) return cardBacks.value;
  return cardBacks.value.filter((asset) =>
    [asset.label, asset.original_filename, asset.checksum].some((value) => value.toLocaleLowerCase().includes(query)),
  );
});
const librarySummary = computed(() =>
  `${cardBacks.value.length} uploaded card back${cardBacks.value.length === 1 ? '' : 's'}.`,
);

const loadCardBackData = async (): Promise<void> => {
  loading.value = true;
  errorMessage.value = '';
  try {
    [cardBacks.value, defaults.value] = await Promise.all([fetchCardBacks(), fetchCardBackDefaults()]);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Card backs could not be loaded.');
  } finally {
    loading.value = false;
  }
};

const selectUploadFile = (event: Event): void => {
  selectedFile.value = (event.target as HTMLInputElement | null)?.files?.[0] ?? null;
};

const uploadSelectedCardBack = async (): Promise<void> => {
  if (!selectedFile.value || uploading.value) return;
  uploading.value = true;
  errorMessage.value = '';
  try {
    await uploadCardBack(selectedFile.value, uploadLabel.value);
    selectedFile.value = null;
    uploadLabel.value = '';
    if (fileInput.value) fileInput.value.value = '';
    await loadCardBackData();
    toast.success('Card-back asset uploaded.');
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Card back could not be uploaded.');
    toast.error(errorMessage.value);
  } finally {
    uploading.value = false;
  }
};

const setDefault = async (cardPool: CardPool, cardBackId: string | null): Promise<void> => {
  if (!cardBackId || settingPool.value !== null || defaults.value[cardPool]?.id === cardBackId) return;
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
const formatDate = (value: string): string => {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString();
};

onMounted(() => { void loadCardBackData(); });
</script>
