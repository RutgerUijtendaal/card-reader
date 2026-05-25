<template>
  <aside
    class="page-card flex min-h-0 flex-col"
    :class="stickyToViewport ? 'xl:sticky xl:top-0 xl:h-[calc(100vh-3rem)]' : 'h-full'"
  >
    <div class="app-scrollbar flex-1 space-y-4 overflow-y-auto pr-1">
      <div class="space-y-2">
        <div class="flex items-center justify-between gap-3">
          <div>
            <h3 class="theme-section-title text-lg font-semibold">
              {{ title }}
            </h3>
            <p
              v-if="description"
              class="theme-section-muted text-sm"
            >
              {{ description }}
            </p>
          </div>
          <button
            class="btn-secondary inline-flex h-11 w-11 shrink-0 items-center justify-center px-0"
            type="button"
            title="Reset filters"
            aria-label="Reset filters"
            @click="onReset"
          >
            <RotateCcw class="h-4 w-4" />
          </button>
        </div>

        <div class="space-y-2">
          <input
            :value="query"
            class="input-base"
            :placeholder="searchPlaceholder"
            @input="onUpdateQuery(($event.target as HTMLInputElement).value)"
          >
          <p class="theme-section-muted text-xs">
            {{ totalCount }} results
          </p>
        </div>
      </div>

      <slot />
    </div>

    <div
      v-if="$slots.footer"
      class="theme-divider mt-4 flex flex-wrap gap-2 border-t pt-4"
    >
      <slot name="footer" />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { RotateCcw } from 'lucide-vue-next';

withDefaults(
  defineProps<{
    title: string;
    description?: string;
    query: string;
    onUpdateQuery: (value: string) => void;
    searchPlaceholder: string;
    totalCount: number;
    onReset: () => void;
    stickyToViewport?: boolean;
  }>(),
  {
    description: undefined,
    stickyToViewport: true,
  },
);
</script>
