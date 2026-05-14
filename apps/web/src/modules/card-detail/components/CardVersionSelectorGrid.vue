<template>
  <div class="page-card">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div>
        <h3 class="text-sm font-semibold text-slate-900">
          {{ title }}
        </h3>
        <p class="text-xs text-slate-500">
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
          ? 'border-slate-900 bg-slate-900 text-white shadow-lg'
          : 'border-slate-200 bg-white text-slate-900 hover:border-slate-300 hover:shadow-sm'"
        @click="$emit('select', version.version_id)"
      >
        <div class="mb-3 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
          <img
            v-if="version.image_url"
            :src="toAbsoluteApiUrl(version.image_url)"
            alt="Card version thumbnail"
            class="h-48 w-full object-contain"
          >
          <div
            v-else
            class="flex h-48 items-center justify-center text-xs text-slate-400"
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
              ? 'bg-white/15 text-white'
              : version.is_latest
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-slate-100 text-slate-600'"
          >
            {{ version.is_latest ? 'Latest' : 'History' }}
          </span>
        </div>
        <p
          class="mt-1 text-xs"
          :class="version.version_id === selectedVersionId ? 'text-slate-200' : 'text-slate-500'"
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
