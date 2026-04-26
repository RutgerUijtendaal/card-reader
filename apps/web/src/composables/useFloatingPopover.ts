import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, nextTick, onBeforeUnmount, ref, watch, type ComputedRef, type Ref } from 'vue';

type MaybeElement = HTMLElement | null;

export type UseFloatingPopoverResult = {
  isOpen: Ref<boolean>;
  triggerRef: Ref<MaybeElement>;
  panelRef: Ref<MaybeElement>;
  x: ComputedRef<number>;
  y: ComputedRef<number>;
  toggle: () => void;
  close: () => void;
};

export const useFloatingPopover = (): UseFloatingPopoverResult => {
  const isOpen = ref(false);
  const triggerRef = ref<MaybeElement>(null);
  const panelRef = ref<MaybeElement>(null);

  const floating = useFloating(triggerRef, panelRef, {
    open: isOpen,
    placement: 'bottom-start',
    strategy: 'fixed',
    middleware: [offset(8), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });
  const x = computed(() => floating.x.value ?? 0);
  const y = computed(() => floating.y.value ?? 0);

  const removeDocListeners = (): void => {
    document.removeEventListener('mousedown', onDocumentMouseDown);
    document.removeEventListener('keydown', onDocumentKeyDown);
  };

  const close = (): void => {
    isOpen.value = false;
  };

  const onDocumentMouseDown = (event: MouseEvent): void => {
    const target = event.target as Node | null;
    const trigger = triggerRef.value;
    const panel = panelRef.value;
    if (!target || !trigger || !panel) return;
    if (trigger.contains(target) || panel.contains(target)) return;
    close();
  };

  const onDocumentKeyDown = (event: KeyboardEvent): void => {
    if (event.key === 'Escape') {
      close();
    }
  };

  const setupOpenState = async (): Promise<void> => {
    await nextTick();
    document.addEventListener('mousedown', onDocumentMouseDown);
    document.addEventListener('keydown', onDocumentKeyDown);
  };

  const teardownOpenState = (): void => {
    removeDocListeners();
  };

  watch(isOpen, (open) => {
    if (open) {
      void setupOpenState();
      return;
    }
    teardownOpenState();
  });

  const toggle = (): void => {
    isOpen.value = !isOpen.value;
  };

  onBeforeUnmount(() => {
    teardownOpenState();
  });

  return {
    isOpen,
    triggerRef,
    panelRef,
    x,
    y,
    toggle,
    close,
  };
};
