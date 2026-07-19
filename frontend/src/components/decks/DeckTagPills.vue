<template>
  <div
    v-if="visibleTags.length > 0 || pendingSuggestions.length > 0"
    class="flex min-w-0 flex-wrap gap-1.5"
  >
    <span
      v-for="tag in visibleTags"
      :key="tag.id"
      class="theme-pill px-2 py-1 text-xs font-semibold"
      :class="tag.kind === 'role' ? 'theme-pill-accent' : 'theme-pill-keyword'"
    >
      {{ tag.label }}
    </span>
    <span
      v-for="suggestion in pendingSuggestions"
      :key="suggestion.id"
      class="theme-pill theme-pill-neutral border border-dashed px-2 py-1 text-xs font-semibold"
      title="Awaiting review"
    >
      {{ suggestion.label }} · Pending
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

const props = withDefaults(defineProps<{
  tags: DeckTagOption[];
  pendingSuggestions?: PendingDeckTagSuggestion[];
  maxVisible?: number;
}>(), {
  pendingSuggestions: () => [],
  maxVisible: 0,
});

const visibleTags = computed(() =>
  props.maxVisible > 0 ? props.tags.slice(0, props.maxVisible) : props.tags,
);
const hiddenCount = computed(() => Math.max(0, props.tags.length - visibleTags.value.length));
</script>
