<template>
  <div class="flex min-w-0 flex-1 items-center gap-4">
    <AppSearchInput
      ref="searchInputRef"
      class="min-w-0 max-w-xl flex-1"
      :model-value="query"
      :placeholder="placeholder"
      @update:model-value="emit('update:query', $event)"
    >
      <template
        v-if="enableSearchHotkey"
        #trailing
      >
        <span class="theme-hotkey-chip">/</span>
      </template>
    </AppSearchInput>
    <p
      class="theme-section-muted shrink-0 text-sm tabular-nums"
      aria-live="polite"
    >
      {{ countLabel }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import AppSearchInput from '@/shared/components/app/AppSearchInput.vue';
import { usePrimarySearchTarget } from '@/shared/composables/usePrimarySearch';

const props = withDefaults(
  defineProps<{
    query: string;
    placeholder: string;
    totalCount: number;
    /** Noun for the result count, as [singular, plural]. */
    resultNoun?: readonly [string, string];
    enableSearchHotkey?: boolean;
  }>(),
  {
    resultNoun: () => ['result', 'results'],
    enableSearchHotkey: true,
  },
);

const emit = defineEmits<{
  'update:query': [value: string];
}>();

type AppSearchInputInstance = InstanceType<typeof AppSearchInput>;

const searchInputRef = ref<AppSearchInputInstance | null>(null);
const searchInputElement = computed(() => searchInputRef.value?.inputElement ?? null);
const countLabel = computed(() => {
  const [singular, plural] = props.resultNoun;
  return `${props.totalCount} ${props.totalCount === 1 ? singular : plural}`;
});

usePrimarySearchTarget(searchInputElement, () => props.enableSearchHotkey);
</script>
