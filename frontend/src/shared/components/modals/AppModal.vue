<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      :class="overlayClass"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="ariaLabelledby || undefined"
      :aria-describedby="ariaDescribedby || undefined"
      @click.self="requestClose"
    >
      <div
        ref="panelRef"
        :class="panelClass"
        tabindex="-1"
      >
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { onKeyStroke, useScrollLock } from '@vueuse/core';

const props = withDefaults(
  defineProps<{
    open: boolean;
    ariaLabelledby?: string;
    ariaDescribedby?: string;
    panelClass?: string;
    overlayClass?: string;
    closeDisabled?: boolean;
    closeOnOverlay?: boolean;
    closeOnEscape?: boolean;
  }>(),
  {
    ariaLabelledby: '',
    ariaDescribedby: '',
    panelClass: 'theme-popover w-full max-w-lg shadow-xl',
    overlayClass: 'theme-overlay',
    closeDisabled: false,
    closeOnOverlay: true,
    closeOnEscape: true,
  },
);

const emit = defineEmits<{
  close: [];
}>();

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[contenteditable="true"]',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

const panelRef = ref<HTMLElement | null>(null);
const bodyScrollLocked = useScrollLock(typeof document === 'undefined' ? null : document.body);
let previouslyFocusedElement: HTMLElement | null = null;

const restorePreviousFocus = (): void => {
  const focusTarget = previouslyFocusedElement;
  previouslyFocusedElement = null;
  if (focusTarget?.isConnected) {
    focusTarget.focus();
  }
};

const focusableElements = (): HTMLElement[] => {
  if (!panelRef.value) {
    return [];
  }
  return Array.from(panelRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (element) => element.getAttribute('aria-hidden') !== 'true',
  );
};

const requestClose = (): void => {
  if (!props.closeDisabled && props.closeOnOverlay) {
    emit('close');
  }
};

onKeyStroke('Escape', (event) => {
  if (!props.open || props.closeDisabled || !props.closeOnEscape) {
    return;
  }
  event.preventDefault();
  emit('close');
});

onKeyStroke('Tab', (event) => {
  const panel = panelRef.value;
  if (!props.open || !panel) {
    return;
  }

  const focusable = focusableElements();
  if (focusable.length === 0) {
    event.preventDefault();
    panel.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable.at(-1);
  const activeElement = document.activeElement;
  if (!first || !last) {
    return;
  }

  if (
    event.shiftKey &&
    (activeElement === first || activeElement === panel || !panel.contains(activeElement))
  ) {
    event.preventDefault();
    last.focus();
  } else if (
    !event.shiftKey &&
    (activeElement === last || activeElement === panel || !panel.contains(activeElement))
  ) {
    event.preventDefault();
    first.focus();
  }
});

watch(
  () => props.open,
  async (open) => {
    bodyScrollLocked.value = open;
    if (open) {
      previouslyFocusedElement =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
      await nextTick();
      if (props.open) {
        panelRef.value?.focus();
      }
      return;
    }

    await nextTick();
    if (!props.open) {
      restorePreviousFocus();
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  bodyScrollLocked.value = false;
  restorePreviousFocus();
});
</script>
