import { autoUpdate, flip, offset, shift, useFloating, type Placement } from '@floating-ui/vue';
import { onClickOutside, onKeyStroke } from '@vueuse/core';
import { computed, ref, type ComputedRef, type Ref } from 'vue';

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

export const useFloatingPopover = (
  options: {
    placement?: Placement;
  } = {},
): UseFloatingPopoverResult => {
  const isOpen = ref(false);
  const triggerRef = ref<MaybeElement>(null);
  const panelRef = ref<MaybeElement>(null);

  const floating = useFloating(triggerRef, panelRef, {
    open: isOpen,
    placement: options.placement ?? 'bottom-start',
    strategy: 'fixed',
    middleware: [offset(8), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });
  const x = computed(() => floating.x.value ?? 0);
  const y = computed(() => floating.y.value ?? 0);

  const close = (): void => {
    isOpen.value = false;
  };

  onClickOutside(panelRef, (event) => {
    if (!isOpen.value) {
      return;
    }

    const target = event.target as Node | null;
    if (target && triggerRef.value?.contains(target)) {
      return;
    }

    close();
  });

  onKeyStroke('Escape', () => {
    if (isOpen.value) {
      close();
    }
  });

  const toggle = (): void => {
    isOpen.value = !isOpen.value;
  };

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
