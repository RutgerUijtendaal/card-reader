<template>
  <div class="page-card grid min-h-[34rem] gap-5 xl:h-[calc(100vh-10rem)] xl:grid-cols-[minmax(18rem,24rem)_minmax(0,1fr)]">
    <section class="flex min-h-0 flex-col gap-4">
      <div class="theme-divider border-b pb-4">
        <h3 class="theme-section-title text-base font-semibold">
          Card backs
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          Manage the default back used by shared card-back experiences.
        </p>
      </div>

      <div class="theme-muted-panel p-4">
        <h4 class="theme-section-title text-sm font-semibold">
          Current
        </h4>
        <div class="mt-4 theme-card-frame theme-card-image-well mx-auto aspect-[63/88] w-full max-w-64 overflow-hidden rounded-xl">
          <img
            v-if="currentCardBack?.image_url"
            class="h-full w-full object-cover"
            :src="toAbsoluteApiUrl(currentCardBack.image_url)"
            :alt="currentCardBack.label"
          >
          <div
            v-else
            class="theme-section-muted flex h-full items-center justify-center p-6 text-center text-sm"
          >
            No card back
          </div>
        </div>
        <div
          v-if="currentCardBack"
          class="mt-4 space-y-1 text-sm"
        >
          <p class="theme-section-title font-semibold">
            {{ currentCardBack.label }}
          </p>
          <p class="theme-section-muted">
            {{ currentCardBack.width }} x {{ currentCardBack.height }}
          </p>
        </div>
      </div>

      <form
        class="theme-muted-panel grid gap-3 p-4"
        @submit.prevent="uploadSelectedCardBack"
      >
        <label class="field-label">
          Label
          <input
            v-model="uploadLabel"
            class="input-base"
            placeholder="Default card back"
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
        <p
          v-if="errorMessage"
          class="theme-alert-danger"
        >
          {{ errorMessage }}
        </p>
        <button
          class="btn-primary justify-center"
          type="submit"
          :disabled="!selectedFile || uploading"
        >
          {{ uploading ? 'Uploading...' : 'Upload And Set Current' }}
        </button>
      </form>
    </section>

    <section class="flex min-h-0 flex-col">
      <div class="theme-divider flex flex-wrap items-start justify-between gap-3 border-b pb-4">
        <div>
          <h3 class="theme-section-title text-base font-semibold">
            History
          </h3>
          <p class="theme-section-muted mt-1 text-sm">
            {{ historySummary }}
          </p>
        </div>
        <button
          class="btn-secondary"
          type="button"
          :disabled="loading"
          @click="loadCardBacks"
        >
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>

      <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto pt-4">
        <div
          v-if="loading"
          class="theme-section-muted text-sm"
        >
          Loading card backs...
        </div>
        <div
          v-else-if="cardBacks.length === 0"
          class="theme-empty-state rounded-lg p-8 text-center text-sm"
        >
          No card backs uploaded.
        </div>
        <div
          v-else
          class="grid gap-3"
        >
          <article
            v-for="cardBack in cardBacks"
            :key="cardBack.id"
            class="theme-card-frame grid gap-4 rounded-lg p-3 sm:grid-cols-[5rem_minmax(0,1fr)_auto]"
            :class="cardBack.is_current ? 'theme-selected-surface' : ''"
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

            <div class="min-w-0 space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <h4 class="theme-section-title truncate text-sm font-semibold">
                  {{ cardBack.label }}
                </h4>
                <span
                  v-if="cardBack.is_current"
                  class="theme-pill theme-pill-success px-2 py-0.5 text-xs font-semibold"
                >
                  Current
                </span>
              </div>
              <p class="theme-section-muted truncate text-xs">
                {{ cardBack.original_filename }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ cardBack.width }} x {{ cardBack.height }} - {{ formatDate(cardBack.created_at) }}
              </p>
            </div>

            <div class="flex items-center sm:justify-end">
              <button
                class="btn-secondary justify-center"
                type="button"
                :disabled="cardBack.is_current || activatingId === cardBack.id"
                @click="setCurrentCardBack(cardBack.id)"
              >
                {{ activatingId === cardBack.id ? 'Setting...' : 'Set Current' }}
              </button>
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
import { toAbsoluteApiUrl } from '@/api/client';
import { activateCardBack, fetchCardBacks, uploadCardBack } from '@/modules/admin/api/cardBacks';
import type { CardBackRecord } from '@/modules/admin/types';

const cardBacks = ref<CardBackRecord[]>([]);
const loading = ref(false);
const uploading = ref(false);
const activatingId = ref<string | null>(null);
const selectedFile = ref<File | null>(null);
const uploadLabel = ref('');
const errorMessage = ref('');
const fileInput = ref<HTMLInputElement | null>(null);

const currentCardBack = computed(() => cardBacks.value.find((cardBack) => cardBack.is_current) ?? null);
const historySummary = computed(() => {
  if (cardBacks.value.length === 0) {
    return 'Upload a card back to create the first history entry.';
  }
  return `${cardBacks.value.length} uploaded card back${cardBacks.value.length === 1 ? '' : 's'}.`;
});

const loadCardBacks = async (): Promise<void> => {
  loading.value = true;
  errorMessage.value = '';
  try {
    cardBacks.value = await fetchCardBacks();
  } catch (error) {
    console.error('Load card backs failed', error);
    errorMessage.value = extractErrorMessage(error, 'Card backs could not be loaded.');
  } finally {
    loading.value = false;
  }
};

const selectUploadFile = (event: Event): void => {
  const input = event.target as HTMLInputElement | null;
  selectedFile.value = input?.files?.[0] ?? null;
};

const uploadSelectedCardBack = async (): Promise<void> => {
  if (!selectedFile.value || uploading.value) return;
  uploading.value = true;
  errorMessage.value = '';
  try {
    await uploadCardBack(selectedFile.value, uploadLabel.value);
    selectedFile.value = null;
    uploadLabel.value = '';
    if (fileInput.value) {
      fileInput.value.value = '';
    }
    await loadCardBacks();
    toast.success('Card back uploaded.');
  } catch (error) {
    console.error('Upload card back failed', error);
    errorMessage.value = extractErrorMessage(error, 'Card back could not be uploaded.');
    toast.error(errorMessage.value);
  } finally {
    uploading.value = false;
  }
};

const setCurrentCardBack = async (cardBackId: string): Promise<void> => {
  if (activatingId.value !== null) return;
  activatingId.value = cardBackId;
  errorMessage.value = '';
  try {
    await activateCardBack(cardBackId);
    await loadCardBacks();
    toast.success('Current card back updated.');
  } catch (error) {
    console.error('Activate card back failed', error);
    errorMessage.value = extractErrorMessage(error, 'Current card back could not be updated.');
    toast.error(errorMessage.value);
  } finally {
    activatingId.value = null;
  }
};

const formatDate = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const maybeResponse = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = maybeResponse?.data?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
  }
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};

onMounted(() => {
  void loadCardBacks();
});
</script>
