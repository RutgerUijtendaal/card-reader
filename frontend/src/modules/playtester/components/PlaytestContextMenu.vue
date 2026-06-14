<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="panelRef"
      class="playtest-context-menu theme-popover"
      :style="floatingStyles"
      data-testid="playtest-context-menu"
      @contextmenu.prevent
    >
      <button
        v-for="action in actions"
        :key="action.id"
        class="playtest-context-menu-action"
        type="button"
        :disabled="action.disabled"
        @click="runAction(action)"
      >
        {{ action.label }}
      </button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { flip, offset, shift, useFloating } from '@floating-ui/vue';
import { onClickOutside, onKeyStroke } from '@vueuse/core';
import { computed, ref } from 'vue';
import type { PlaytestEntityAction } from '@/modules/playtester/types';

const props = defineProps<{
  open: boolean;
  x: number;
  y: number;
  actions: PlaytestEntityAction[];
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const panelRef = ref<HTMLElement | null>(null);
const virtualReference = computed(() => ({
  getBoundingClientRect: () => ({
    x: props.x,
    y: props.y,
    top: props.y,
    right: props.x,
    bottom: props.y,
    left: props.x,
    width: 0,
    height: 0,
    toJSON: () => undefined,
  }),
}));
const { floatingStyles } = useFloating(virtualReference, panelRef, {
  placement: 'right-start',
  strategy: 'fixed',
  middleware: [offset(4), flip(), shift({ padding: 8 })],
});

const runAction = (action: PlaytestEntityAction): void => {
  if (action.disabled) {
    return;
  }
  action.run();
  emit('close');
};

onClickOutside(panelRef, () => {
  emit('close');
});

onKeyStroke('Escape', () => {
  emit('close');
});
</script>

<style scoped>
.playtest-context-menu {
  position: fixed;
  z-index: 10001;
  display: grid;
  width: 13.5rem;
  max-height: calc(100vh - 1rem);
  gap: 0.25rem;
  overflow: auto;
  padding: 0.45rem;
}

.playtest-context-menu-action {
  border-radius: 0.45rem;
  padding: 0.55rem 0.65rem;
  color: var(--color-text);
  font-size: 0.78rem;
  font-weight: 700;
  text-align: left;
  transition:
    background 120ms ease,
    color 120ms ease;
}

.playtest-context-menu-action:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-accent) 16%, transparent);
  color: var(--color-text-strong);
}

.playtest-context-menu-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
</style>
