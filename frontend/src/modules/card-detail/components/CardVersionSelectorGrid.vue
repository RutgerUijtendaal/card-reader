<template>
  <div :class="surface === 'plain' ? 'py-2' : 'page-card py-4'">
    <div class="mb-2 flex items-center justify-between gap-3">
      <div>
        <h3 class="theme-section-title text-xs font-semibold uppercase tracking-[0.16em]">
          {{ title }}
        </h3>
        <p class="theme-section-muted text-xs">
          {{ description }}
        </p>
      </div>
    </div>

    <div
      class="grid gap-2"
      :class="layout === 'stack' ? 'grid-cols-1' : 'sm:grid-cols-2 2xl:grid-cols-3'"
    >
      <div
        v-for="version in versions"
        :key="version.version_id"
        class="group relative flex min-w-0 items-center gap-3 rounded-lg border px-2.5 py-2 text-left transition"
        :class="version.version_id === selectedVersionId
          ? 'theme-selected-surface-strong'
          : 'theme-card-frame theme-section-title hover:border-[var(--theme-border-strong)]'"
      >
        <button
          type="button"
          class="flex min-w-0 flex-1 items-center gap-3 text-left"
          @click="$emit('select', version.version_id)"
        >
          <div class="theme-card-frame-muted theme-card-image-well h-16 w-12 shrink-0 rounded-md">
            <img
              v-if="version.image_url"
              :src="toAbsoluteApiUrl(version.image_url)"
              alt="Card printing thumbnail"
              class="h-full w-full object-contain"
            >
            <div
              v-else
              class="theme-kicker flex h-full items-center justify-center text-[10px]"
            >
              No image
            </div>
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <p class="truncate text-sm font-semibold">
                Printing {{ version.version_number }}
              </p>
              <span
                class="whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-medium"
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
              class="mt-0.5 truncate text-xs"
              :class="version.version_id === selectedVersionId ? 'theme-section-title' : 'theme-section-muted'"
            >
              {{ formatDate(version.created_at) }}
            </p>
            <p
              class="mt-0.5 truncate text-xs"
              :class="version.version_id === selectedVersionId ? 'theme-section-title' : 'theme-section-muted'"
            >
              Version {{ formatCardContentVersion(version) }}
            </p>
          </div>
        </button>

        <button
          v-if="allowPromote && !version.is_latest"
          class="btn-secondary absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center p-0 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100"
          type="button"
          :disabled="promotingVersionId === version.version_id"
          :title="`Make printing ${version.version_number} the latest version`"
          @click.stop="$emit('promote', version.version_id)"
        >
          <ArrowUpCircle class="h-4 w-4" />
          <span class="sr-only">
            Make printing {{ version.version_number }} latest
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowUpCircle } from 'lucide-vue-next';
import { formatCardContentVersion, type CardVersionDetail } from '@/modules/card-detail/types';

withDefaults(
  defineProps<{
    versions: CardVersionDetail[];
    selectedVersionId: string;
    toAbsoluteApiUrl: (urlPath: string) => string;
    formatDate: (value: string) => string;
    title?: string;
    description?: string;
    layout?: 'grid' | 'stack';
    surface?: 'card' | 'plain';
    allowPromote?: boolean;
    promotingVersionId?: string | null;
  }>(),
  {
    title: 'Printings',
    description: 'Select a printing to inspect or edit.',
    layout: 'grid',
    surface: 'card',
    allowPromote: false,
    promotingVersionId: null,
  },
);

defineEmits<{
  (e: 'select', versionId: string): void;
  (e: 'promote', versionId: string): void;
}>();
</script>
