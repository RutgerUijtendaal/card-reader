<template>
  <AppStickyAside
    :root-class="stickyToViewport ? '' : 'xl:static xl:max-h-none'"
    scroll-class="space-y-4"
  >
    <div class="space-y-2">
      <div class="flex justify-between gap-3">
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
        <AppSearchInput
          ref="searchInputRef"
          :model-value="query"
          :placeholder="searchPlaceholder"
          @update:model-value="onUpdateQuery"
        >
          <template
            v-if="showSearchHotkeyHint"
            #trailing
          >
            <span class="theme-hotkey-chip">/</span>
          </template>
        </AppSearchInput>
        <p class="theme-section-muted text-xs">
          {{ totalCount }} results
        </p>
      </div>
    </div>

    <slot />

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
import { computed, ref } from 'vue';
import { RotateCcw } from 'lucide-vue-next';
import AppSearchInput from '@/components/app/AppSearchInput.vue';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import { usePrimarySearchTarget } from '@/composables/useHotkeys';

const props = withDefaults(
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

type AppSearchInputInstance = InstanceType<typeof AppSearchInput>;

const searchInputRef = ref<AppSearchInputInstance | null>(null);
const searchInputElement = computed(() => searchInputRef.value?.inputElement ?? null);
const showSearchHotkeyHint = computed(() => props.enableSearchHotkey);

usePrimarySearchTarget(searchInputElement, () => props.enableSearchHotkey);
</script>
