<template>
  <div class="page-card">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div>
        <h3 class="theme-section-title text-sm font-semibold">
          {{ title }}
        </h3>
        <p class="theme-section-muted text-xs">
          {{ description }}
        </p>
      </div>
    </div>

    <div class="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
      <button
        v-for="version in versions"
        :key="version.version_id"
        type="button"
        class="rounded-xl border p-3 text-left transition"
        :class="version.version_id === selectedVersionId
          ? 'theme-selected-surface-strong shadow-lg'
          : 'theme-card-frame theme-section-title hover:-translate-y-0.5'"
        @click="$emit('select', version.version_id)"
      >
        <div class="theme-card-frame-muted theme-card-image-well mb-3 rounded-lg">
          <img
            v-if="version.image_url"
            :src="toAbsoluteApiUrl(version.image_url)"
            alt="Card version thumbnail"
            class="h-48 w-full object-contain"
          >
          <div
            v-else
            class="theme-kicker flex h-48 items-center justify-center text-xs"
          >
            No image
          </div>
        </div>
        <div class="flex items-center justify-between gap-2">
          <p class="text-sm font-semibold">
            Version {{ version.version_number }}
          </p>
          <span
            class="rounded-full px-2 py-0.5 text-[10px] font-medium"
            :class="version.version_id === selectedVersionId
              ? 'theme-pill-neutral'
              : version.is_latest
                ? 'theme-pill-success'
                : 'theme-pill-neutral'"
          >
            {{ version.is_latest ? 'Latest' : 'History' }}
          </span>
        </div>
        <p
          class="mt-1 text-xs"
          :class="version.version_id === selectedVersionId ? 'theme-section-title' : 'theme-section-muted'"
        >
          {{ formatDate(version.created_at) }}
        </p>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CardVersionDetail } from '@/modules/card-detail/types';

withDefaults(
  defineProps<{
    versions: CardVersionDetail[];
    selectedVersionId: string;
    toAbsoluteApiUrl: (urlPath: string) => string;
    formatDate: (value: string) => string;
    title?: string;
    description?: string;
  }>(),
  {
    title: 'Card Versions',
    description: 'Select a version to inspect or edit.',
  },
);

defineEmits<{
  (e: 'select', versionId: string): void;
}>();
</script>
