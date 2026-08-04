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
    <button
      v-if="hiddenCount > 0"
      class="theme-pill theme-pill-neutral cursor-pointer px-2 py-1 text-xs font-semibold transition hover:border-[var(--color-border-strong)] hover:text-[var(--color-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--theme-accent)]"
      type="button"
      :aria-label="`Show all ${orderedItems.length} deck tags`"
      :aria-expanded="expanded"
      @click="expanded = true"
    >
      +{{ hiddenCount }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { DeckTagOption, PendingDeckTagSuggestion } from '@/domain/decks/types';

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

const expanded = ref(false);

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
  props.maxVisible > 0 && !expanded.value
    ? orderedItems.value.slice(0, props.maxVisible)
    : orderedItems.value,
);
const hiddenCount = computed(() => Math.max(0, orderedItems.value.length - visibleItems.value.length));
</script>
