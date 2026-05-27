<template>
  <div class="relative">
    <button
      ref="triggerRef"
      type="button"
      class="theme-card-frame-muted theme-icon-button theme-section-title inline-flex h-10 w-10 items-center justify-center rounded-lg"
      :aria-label="buttonLabel"
      :title="buttonLabel"
      @click="toggle"
    >
      <Ellipsis class="h-4 w-4" />
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-40 w-[15rem] p-3"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-3">
          <slot :close="close" />
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { Ellipsis } from 'lucide-vue-next';
import { useFloatingPopover } from '@/composables/useFloatingPopover';

withDefaults(
  defineProps<{
    buttonLabel?: string;
  }>(),
  {
    buttonLabel: 'Open extra actions',
  },
);

const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover({
  placement: 'bottom-end',
});
</script>
