<template>
  <div
    class="theme-tablist app-scrollbar w-auto max-w-full flex-nowrap overflow-x-auto"
    role="tablist"
    :aria-label="label"
  >
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      role="tab"
      class="theme-tab shrink-0 gap-2 px-3"
      :class="{ 'theme-tab-active': tab.id === modelValue }"
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
.board-tab-count {
  border-radius: 9999px;
  padding: 0 0.4rem;
  font-size: 0.7rem;
  line-height: 1.15rem;
  background: var(--color-pill-neutral-bg);
  color: var(--color-text-muted);
}

.theme-tab-active .board-tab-count {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--color-selected-text);
}
</style>
