<template>
  <div
    v-if="visibleItems.length > 0"
    class="flex min-w-0 flex-wrap gap-1.5"
  >
    <span
      v-for="item in visibleItems"
      :key="item.key"
      class="theme-pill px-2 py-1 text-xs font-semibold"
      :class="item.kind === 'role'
        ? 'theme-pill-accent'
        : item.kind === 'type'
          ? 'theme-pill-keyword'
          : 'theme-pill-neutral border border-dashed'"
      :title="item.kind === 'pending' ? 'Awaiting review' : undefined"
    >
      {{ item.label }}<template v-if="item.kind === 'pending'"> · Pending</template>
    </span>
    <span
      v-if="hiddenCount > 0"
      class="theme-pill theme-pill-neutral px-2 py-1 text-xs font-semibold"
    >
      +{{ hiddenCount }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { DeckTagOption, PendingDeckTagSuggestion } from '@/modules/decks/types';

type VisibleDeckTagItem = {
  key: string;
  label: string;
  kind: 'role' | 'type' | 'pending';
};

const props = withDefaults(defineProps<{
  tags: DeckTagOption[];
  pendingSuggestions?: PendingDeckTagSuggestion[];
  maxVisible?: number;
}>(), {
  pendingSuggestions: () => [],
  maxVisible: 0,
});

const orderedItems = computed<VisibleDeckTagItem[]>(() => [
  ...props.tags
    .filter((tag) => tag.kind === 'role')
    .map((tag) => ({ key: `tag:${tag.id}`, label: tag.label, kind: tag.kind })),
  ...props.tags
    .filter((tag) => tag.kind === 'type')
    .map((tag) => ({ key: `tag:${tag.id}`, label: tag.label, kind: tag.kind })),
  ...props.pendingSuggestions.map((suggestion) => ({
    key: `suggestion:${suggestion.id}`,
    label: suggestion.label,
    kind: 'pending' as const,
  })),
]);
const visibleItems = computed(() =>
  props.maxVisible > 0 ? orderedItems.value.slice(0, props.maxVisible) : orderedItems.value,
);
const hiddenCount = computed(() => Math.max(0, orderedItems.value.length - visibleItems.value.length));
</script>
