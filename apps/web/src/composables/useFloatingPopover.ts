import { autoUpdate, computePosition, flip, offset, shift } from '@floating-ui/dom';
import { nextTick, onBeforeUnmount, ref, watch, type Ref } from 'vue';

type MaybeElement = HTMLElement | null;

export type UseFloatingPopoverResult = {
  isOpen: Ref<boolean>;
  triggerRef: Ref<MaybeElement>;
  panelRef: Ref<MaybeElement>;
  x: Ref<number>;
  y: Ref<number>;
  toggle: () => void;
  close: () => void;
};

export const useFloatingPopover = (): UseFloatingPopoverResult => {
  const isOpen = ref(false);
  const triggerRef = ref<MaybeElement>(null);
  const panelRef = ref<MaybeElement>(null);
  const x = ref(0);
  const y = ref(0);

  let stopAutoUpdate: (() => void) | null = null;

  const updatePosition = async (): Promise<void> => {
    const trigger = triggerRef.value;
    const panel = panelRef.value;
    if (!trigger || !panel) return;

    const position = await computePosition(trigger, panel, {
      placement: 'bottom-start',
      middleware: [offset(8), flip(), shift({ padding: 8 })],
    });
    x.value = position.x;
    y.value = position.y;
  };

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
    const trigger = triggerRef.value;
    const panel = panelRef.value;
    if (!trigger || !panel) return;

    await updatePosition();
    stopAutoUpdate = autoUpdate(trigger, panel, updatePosition);
    document.addEventListener('mousedown', onDocumentMouseDown);
    document.addEventListener('keydown', onDocumentKeyDown);
  };

  const teardownOpenState = (): void => {
    if (stopAutoUpdate) {
      stopAutoUpdate();
      stopAutoUpdate = null;
    }
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
