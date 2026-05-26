<template>
  <span
    ref="triggerRef"
    class="inline-flex"
    tabindex="0"
    :aria-describedby="tooltipId"
    @mouseenter="open"
    @mouseleave="close"
    @focusin="open"
    @focusout="close"
  >
    <slot />
  </span>

  <Teleport to="body">
    <div
      v-if="isOpen"
      :id="tooltipId"
      ref="panelRef"
      role="tooltip"
      class="theme-popover pointer-events-none z-50 max-w-xs px-3 py-2 text-xs leading-5 shadow-lg"
      :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
    >
      {{ text }}
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating, type Placement } from '@floating-ui/vue';
import { computed, ref } from 'vue';

const props = withDefaults(
  defineProps<{
    text: string;
    placement?: Placement;
  }>(),
  {
    placement: 'top',
  },
);

const isOpen = ref(false);
const triggerRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const tooltipId = `info-tooltip-${Math.random().toString(36).slice(2, 10)}`;

const floating = useFloating(triggerRef, panelRef, {
  open: isOpen,
  placement: props.placement,
  strategy: 'fixed',
  middleware: [offset(10), flip(), shift({ padding: 8 })],
  whileElementsMounted: autoUpdate,
});

const x = computed(() => floating.x.value ?? 0);
const y = computed(() => floating.y.value ?? 0);

const open = (): void => {
  isOpen.value = true;
};

const close = (): void => {
  isOpen.value = false;
};
</script>
