<template>
  <section class="grid h-[calc(100vh-12rem)] min-h-[34rem] gap-6 overflow-hidden xl:grid-cols-[22rem_minmax(0,1fr)]">
    <aside class="page-card flex min-h-0 flex-col overflow-hidden">
      <div class="theme-divider border-b pb-4">
        <h3 class="theme-section-title text-base font-semibold">
          Versions
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          Select a content version to inspect its imported cards.
        </p>
      </div>

      <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto py-4">
        <div
          v-if="isLoadingVersions"
          class="theme-section-muted text-sm"
        >
          Loading versions...
        </div>
        <div
          v-else-if="versions.length === 0"
          class="theme-empty-state rounded-lg p-4 text-sm"
        >
          No versions found.
        </div>
        <div
          v-else
          class="grid gap-2"
        >
          <button
            v-for="version in versions"
            :key="version.id"
            class="rounded-lg border px-3 py-3 text-left transition"
            type="button"
            :class="version.id === selectedVersionId
              ? 'theme-selected-surface-strong'
              : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'"
            @click="selectVersion(version.id)"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold">
                  {{ version.version_number }}
                </p>
                <p
                  class="mt-1 truncate text-xs"
                  :class="version.id === selectedVersionId ? 'theme-section-title' : 'theme-section-muted'"
                >
                  {{ version.description }}
                </p>
              </div>
              <span class="theme-pill theme-pill-neutral shrink-0 px-2 py-0.5 text-xs font-semibold">
                {{ version.card_count }}
              </span>
            </div>
          </button>
        </div>
      </div>

      <form
        v-if="selectedVersion"
        class="theme-divider grid gap-3 border-t pt-4"
        @submit.prevent="saveVersion"
      >
        <label class="field-label">
          Version
          <input
            v-model="versionForm.versionNumber"
            class="input-base"
            type="text"
            inputmode="numeric"
            pattern="[0-9]+\.[0-9]+\.[0-9]+"
            placeholder="14.1.0"
            required
          >
          <span
            v-if="versionNumberError"
            class="text-xs text-rose-400"
          >
            {{ versionNumberError }}
          </span>
        </label>
        <label class="field-label">
          Description
          <textarea
            v-model="versionForm.description"
            class="input-base min-h-24 resize-y"
            required
          />
          <span
            v-if="descriptionError"
            class="text-xs text-rose-400"
          >
            {{ descriptionError }}
          </span>
        </label>
        <p
          v-if="formError"
          class="theme-alert-danger"
        >
          {{ formError }}
        </p>
        <p
          v-if="saveMessage"
          class="theme-alert-success"
        >
          {{ saveMessage }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button
            class="btn-primary"
            type="submit"
            :disabled="!formIsDirty || !formIsValid || isSavingVersion"
          >
            {{ isSavingVersion ? 'Saving...' : 'Save Version' }}
          </button>
          <button
            class="btn-secondary"
            type="button"
            :disabled="!formIsDirty || isSavingVersion"
            @click="resetForm"
          >
            Reset
          </button>
        </div>
      </form>
    </aside>

    <section class="page-card flex min-h-0 flex-col overflow-hidden">
      <div class="theme-divider flex flex-wrap items-start justify-between gap-3 border-b pb-4">
        <div>
          <h3 class="theme-section-title text-base font-semibold">
            Cards
          </h3>
          <p class="theme-section-muted mt-1 text-sm">
            {{ selectedVersion ? `${cards.length} card${cards.length === 1 ? '' : 's'} in ${selectedVersion.version_number}.` : 'Select a version.' }}
          </p>
        </div>
      </div>

      <div class="app-scrollbar min-h-0 flex-1 overflow-y-auto pt-5">
        <p
          v-if="errorMessage"
          class="theme-alert-danger mb-4"
        >
          {{ errorMessage }}
        </p>

        <div
          v-if="isLoadingCards"
          class="theme-section-muted text-sm"
        >
          Loading cards...
        </div>
        <div
          v-else-if="selectedVersion && cards.length === 0"
          class="theme-empty-state rounded-lg p-8 text-center text-sm"
        >
          No cards found for this version.
        </div>
        <div
          v-else
          class="grid gap-6 pr-1"
          :style="galleryGridStyle"
        >
          <CardGalleryItem
            v-for="card in cards"
            :key="card.version_id"
            :card="card"
            :card-height-rem="cardHeightRem"
            :navigation-target="buildAdminCardDetailLocation(card.id, route.query)"
          >
            <template #hover-actions="{ cardItem, isCard }">
              <RouterLink
                v-if="isCard && cardItem"
                :to="buildAdminCardDetailLocation(cardItem.id, route.query)"
                class="btn-secondary pointer-events-auto gap-1.5 rounded-full px-3 py-1.5 text-xs shadow-xl"
              >
                <Pencil class="h-3.5 w-3.5" />
                <span>Edit</span>
              </RouterLink>
            </template>
          </CardGalleryItem>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { Pencil } from 'lucide-vue-next';
import { RouterLink } from 'vue-router';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import { fetchContentVersionCards, fetchContentVersions, updateContentVersion } from '@/modules/admin/api/contentVersions';
import { buildAdminCardDetailLocation } from '@/modules/admin/adminRouteState';
import { useAdminRouteSync } from '@/modules/admin/composables/useAdminRouteSync';
import type { ContentVersionRecord } from '@/modules/admin/types';
import type { CardListItem } from '@/modules/card-detail/types';
import { useGalleryOptions } from '@/modules/card-search/useGalleryOptions';

const versions = ref<ContentVersionRecord[]>([]);
const cards = ref<CardListItem[]>([]);
const selectedVersionId = ref<string | null>(null);
const isLoadingVersions = ref(false);
const isLoadingCards = ref(false);
const isSavingVersion = ref(false);
const errorMessage = ref('');
const formError = ref('');
const saveMessage = ref('');
const versionForm = ref({
  versionNumber: '',
  description: '',
});
const { route } = useAdminRouteSync();
const { cardScale } = useGalleryOptions();

const selectedVersion = computed(
  () => versions.value.find((version) => version.id === selectedVersionId.value) ?? null,
);
const versionNumberError = computed(() =>
  /^\d+\.\d+\.\d+$/.test(versionForm.value.versionNumber.trim())
    ? ''
    : 'Use major.minor.patch format, for example 14.1.0.',
);
const descriptionError = computed(() =>
  versionForm.value.description.trim().length > 0 ? '' : 'Description is required.',
);
const formIsValid = computed(() => versionNumberError.value.length === 0 && descriptionError.value.length === 0);
const formIsDirty = computed(() =>
  selectedVersion.value
    ? versionForm.value.versionNumber.trim() !== selectedVersion.value.version_number
      || versionForm.value.description.trim() !== selectedVersion.value.description
    : false,
);
const cardHeightRem = computed(() => Number((24 * cardScale.value).toFixed(2)));
const galleryGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(auto-fill, minmax(${Math.round(250 * cardScale.value)}px, 1fr))`,
}));

const selectVersion = (versionId: string): void => {
  selectedVersionId.value = versionId;
};

const resetForm = (): void => {
  versionForm.value = {
    versionNumber: selectedVersion.value?.version_number ?? '',
    description: selectedVersion.value?.description ?? '',
  };
  formError.value = '';
  saveMessage.value = '';
};

const updateVersionInList = (updated: ContentVersionRecord): void => {
  versions.value = versions.value
    .map((version) => (version.id === updated.id ? updated : version))
    .sort((left, right) => right.version_number.localeCompare(left.version_number, undefined, { numeric: true }));
};

const extractApiErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }
  }
  if (typeof error === 'object' && error && 'message' in error) {
    const message = String((error as { message: unknown }).message);
    if (message.trim().length > 0) {
      return message;
    }
  }
  return fallback;
};

const saveVersion = async (): Promise<void> => {
  if (!selectedVersion.value) return;
  saveMessage.value = '';
  if (versionNumberError.value) {
    formError.value = versionNumberError.value;
    return;
  }
  if (descriptionError.value) {
    formError.value = descriptionError.value;
    return;
  }
  isSavingVersion.value = true;
  formError.value = '';
  try {
    const updated = await updateContentVersion(selectedVersion.value.id, {
      version_number: versionForm.value.versionNumber.trim(),
      description: versionForm.value.description.trim(),
    });
    updateVersionInList(updated);
    selectedVersionId.value = updated.id;
    versionForm.value = {
      versionNumber: updated.version_number,
      description: updated.description,
    };
    saveMessage.value = 'Version saved.';
  } catch (error) {
    console.error('Save content version failed', error);
    formError.value = extractApiErrorMessage(error, 'Version could not be saved.');
  } finally {
    isSavingVersion.value = false;
  }
};

const loadVersions = async (): Promise<void> => {
  isLoadingVersions.value = true;
  errorMessage.value = '';
  try {
    versions.value = await fetchContentVersions();
    if (!versions.value.some((version) => version.id === selectedVersionId.value)) {
      selectedVersionId.value = versions.value[0]?.id ?? null;
    }
  } catch (error) {
    console.error('Load content versions failed', error);
    errorMessage.value = 'Versions could not be loaded.';
  } finally {
    isLoadingVersions.value = false;
  }
};

const loadCards = async (versionId: string | null): Promise<void> => {
  if (!versionId) {
    cards.value = [];
    return;
  }
  isLoadingCards.value = true;
  errorMessage.value = '';
  try {
    cards.value = await fetchContentVersionCards(versionId);
  } catch (error) {
    console.error('Load content version cards failed', error);
    cards.value = [];
    errorMessage.value = 'Cards could not be loaded.';
  } finally {
    isLoadingCards.value = false;
  }
};

watch(
  selectedVersionId,
  (versionId) => {
    resetForm();
    void loadCards(versionId);
  },
);

watch(
  selectedVersion,
  () => {
    resetForm();
  },
  { immediate: true },
);

onMounted(() => {
  void loadVersions();
});
</script>
