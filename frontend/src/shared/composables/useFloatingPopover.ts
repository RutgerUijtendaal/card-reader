import { autoUpdate, flip, offset, shift, size, useFloating, type Middleware, type Placement } from '@floating-ui/vue';
import { onClickOutside, onKeyStroke } from '@vueuse/core';
import { computed, ref, type ComputedRef, type Ref } from 'vue';

type MaybeElement = HTMLElement | null;

export type UseFloatingPopoverResult = {
  isOpen: Ref<boolean>;
  triggerRef: Ref<MaybeElement>;
  panelRef: Ref<MaybeElement>;
  x: ComputedRef<number>;
  y: ComputedRef<number>;
  availableHeight: Ref<number | null>;
  toggle: () => void;
  close: () => void;
};

export const useFloatingPopover = (
  options: {
    placement?: Placement;
    allowFlip?: boolean;
    fitAvailableHeight?: boolean;
    trackLayoutShift?: boolean;
  } = {},
): UseFloatingPopoverResult => {
  const isOpen = ref(false);
  const triggerRef = ref<MaybeElement>(null);
  const panelRef = ref<MaybeElement>(null);
  const availableHeight = ref<number | null>(null);
  const middleware = computed<Middleware[]>(() => [
    offset(8),
    ...(options.allowFlip ?? true ? [flip()] : []),
    shift({ padding: 8 }),
    ...(options.fitAvailableHeight
      ? [size({
        padding: 8,
        apply({ availableHeight: nextAvailableHeight }) {
          availableHeight.value = Math.max(0, Math.floor(nextAvailableHeight));
        },
      })]
      : []),
  ]);

  const floating = useFloating(triggerRef, panelRef, {
    open: isOpen,
    placement: options.placement ?? 'bottom-start',
    strategy: 'fixed',
    middleware,
    whileElementsMounted: (reference, floatingElement, update) =>
      autoUpdate(reference, floatingElement, update, {
        layoutShift: options.trackLayoutShift ?? true,
      }),
  });
  const x = computed(() => floating.x.value ?? 0);
  const y = computed(() => floating.y.value ?? 0);

  const close = (): void => {
    isOpen.value = false;
    availableHeight.value = null;
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
    if (!isOpen.value) {
      availableHeight.value = null;
    }
  };

  return {
    isOpen,
    triggerRef,
    panelRef,
    x,
    y,
    availableHeight,
    toggle,
    close,
  };
};
