<template>
  <div
    class="app-scrollbar flex max-w-full items-stretch gap-1 overflow-x-auto"
    role="tablist"
    :aria-label="label"
  >
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      role="tab"
      class="board-tab inline-flex h-9 shrink-0 items-center gap-2 px-3 text-sm font-semibold transition"
      :class="{ 'board-tab-active': tab.id === modelValue }"
      :aria-selected="tab.id === modelValue"
      :title="tab.detail"
      @click="emit('update:modelValue', tab.id)"
    >
      <span class="max-w-[12rem] truncate">{{ tab.label }}</span>
      <span class="board-tab-count tabular-nums">{{ tab.count }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
export type AppBoardTab = {
  id: string;
  label: string;
  /** Total cards on the board, shown beside the name. */
  count: number;
  /** Longer description for the tooltip, such as "23 cards, 12 unique". */
  detail?: string;
};

defineProps<{
  /** Accessible name for the tab row, such as "Deck boards". */
  label: string;
  tabs: AppBoardTab[];
  modelValue: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();
</script>

<style scoped>
/* Flat tabs: text on the header surface, the current board marked by an accent underline. */
.board-tab {
  border-bottom: 2px solid transparent;
  color: var(--color-text-muted);
}

.board-tab:hover:not(.board-tab-active) {
  color: var(--color-text);
}

.board-tab-active {
  border-bottom-color: var(--accent);
  color: var(--color-text);
}

.board-tab-count {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-soft);
}

.board-tab-active .board-tab-count {
  color: var(--color-selected-text);
}
</style>
