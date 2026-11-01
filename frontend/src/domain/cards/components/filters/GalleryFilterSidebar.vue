<template>
  <AppStickyAside
    :root-class="stickyToViewport ? '' : 'xl:static xl:max-h-none'"
    scroll-class="space-y-4"
  >
    <div class="space-y-2">
      <div class="flex justify-between gap-3">
        <div>
          <h3 class="theme-section-title text-lg font-semibold">
            <button
              v-if="!isSideColumn"
              type="button"
              class="inline-flex items-center gap-2"
              :aria-expanded="filtersOpen"
              :aria-controls="filtersId"
              @click="filtersOpen = !filtersOpen"
            >
              {{ title }}
              <ChevronDown
                class="h-4 w-4 transition-transform"
                :class="filtersOpen ? 'rotate-180' : ''"
                aria-hidden="true"
              />
            </button>
            <template v-else>
              {{ title }}
            </template>
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

      <AppCollectionSearch
        layout="stacked"
        :query="query"
        :placeholder="searchPlaceholder"
        :total-count="totalCount"
        :enable-search-hotkey="enableSearchHotkey"
        @update:query="onUpdateQuery"
      />
    </div>

    <!-- Below the side-column breakpoint the filters stack above results, so they start folded away. -->
    <div
      v-show="isSideColumn || filtersOpen"
      :id="filtersId"
      class="space-y-4"
    >
      <slot />
    </div>

    <template
      v-if="$slots.footer"
      #footer
    >
      <div class="flex flex-wrap gap-2">
        <slot name="footer" />
      </div>
    </template>
  </AppStickyAside>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue';
import { useMediaQuery } from '@vueuse/core';
import { ChevronDown, RotateCcw } from 'lucide-vue-next';
import AppCollectionSearch from '@/shared/components/app/AppCollectionSearch.vue';
import AppStickyAside from '@/shared/components/app/AppStickyAside.vue';

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
    enableSearchHotkey?: boolean;
  }>(),
  {
    description: undefined,
    stickyToViewport: true,
    enableSearchHotkey: true,
  },
);

const isSideColumn = useMediaQuery('(min-width: 1280px)', { ssrWidth: 1280 });
const filtersOpen = ref(false);
const filtersId = useId();
</script>
