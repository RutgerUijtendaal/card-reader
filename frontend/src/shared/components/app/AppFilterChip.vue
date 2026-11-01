<template>
  <div class="relative">
    <button
      ref="triggerRef"
      type="button"
      class="theme-choice-chip min-h-9 gap-1.5 px-3 py-1"
      :class="{ 'theme-choice-chip-active': activeCount > 0 || isOpen }"
      :aria-expanded="isOpen"
      :aria-controls="panelId"
      @click="toggle"
    >
      <span>{{ label }}</span>
      <span
        v-if="activeCount > 0"
        class="app-filter-chip-count tabular-nums"
        :aria-label="`${activeCount} active`"
      >{{ activeCount }}</span>
      <ChevronDown
        class="h-3.5 w-3.5 transition-transform"
        :class="isOpen ? 'rotate-180' : ''"
        aria-hidden="true"
      />
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        :id="panelId"
        ref="panelRef"
        class="app-filter-chip-panel theme-popover app-scrollbar z-40 overflow-y-auto p-4"
        :class="panelClass"
        role="dialog"
        :aria-label="`${label} filter`"
        :style="{
          position: 'fixed',
          left: `${x}px`,
          top: `${y}px`,
          maxHeight: availableHeight === null ? undefined : `${availableHeight}px`,
        }"
      >
        <slot />
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { useId } from 'vue';
import { ChevronDown } from 'lucide-vue-next';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';

withDefaults(
  defineProps<{
    label: string;
    /** Number of active selections inside this filter, shown on the chip. */
    activeCount?: number;
    panelClass?: string;
  }>(),
  {
    activeCount: 0,
    panelClass: 'w-[22rem] max-w-[calc(100vw-1rem)]',
  },
);

const panelId = useId();
const { isOpen, triggerRef, panelRef, x, y, availableHeight, toggle } = useFloatingPopover({
  placement: 'bottom-start',
  fitAvailableHeight: true,
});
</script>

<style scoped>
.app-filter-chip-count {
  border-radius: 9999px;
  padding: 0 0.4rem;
  font-size: 0.7rem;
  line-height: 1.15rem;
  background: color-mix(in srgb, var(--accent) 20%, transparent);
  color: var(--color-selected-text);
}

/* A filter group inside its own popover needs no leading hairline. */
.app-filter-chip-panel > :deep(.theme-filter-section:first-child) {
  border-top-width: 0;
  padding-top: 0;
}
</style>
