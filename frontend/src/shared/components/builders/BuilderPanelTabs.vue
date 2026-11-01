<template>
  <nav
    class="builder-panel-tabs grid w-full"
    :style="{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }"
    :aria-label="label"
  >
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      class="builder-panel-tab inline-flex h-11 min-w-0 items-center justify-center gap-1.5 px-2 text-sm font-semibold transition"
      :class="{ 'builder-panel-tab-active': tab.active }"
      :aria-pressed="tab.active"
      :disabled="disabled"
      @click="emit('select', tab.id)"
    >
      <component
        :is="tab.icon"
        class="h-4 w-4 shrink-0"
        aria-hidden="true"
      />
      <span class="truncate">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script setup lang="ts" generic="T extends string">
import type { Component } from 'vue';

/**
 * The builder's view switch, attached edge to edge to the collection panel: which part of the
 * card pool is showing, plus the details overlay.
 */
withDefaults(
  defineProps<{
    label: string;
    tabs: readonly { id: T; label: string; icon: Component; active: boolean }[];
    disabled?: boolean;
  }>(),
  { disabled: false },
);

const emit = defineEmits<{
  select: [id: T];
}>();
</script>

<style scoped>
.builder-panel-tabs {
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

.builder-panel-tab {
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  color: var(--color-text-muted);
}

.builder-panel-tab + .builder-panel-tab {
  border-left: 1px solid var(--color-border);
}

.builder-panel-tab:hover:not(:disabled):not(.builder-panel-tab-active) {
  background: var(--color-surface-soft);
  color: var(--color-text);
}

.builder-panel-tab-active {
  border-bottom-color: var(--accent);
  background: var(--color-selected-bg);
  color: var(--color-selected-text);
}

.builder-panel-tab:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
