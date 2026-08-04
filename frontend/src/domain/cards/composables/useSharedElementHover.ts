import { computed, nextTick, onBeforeUnmount, ref, watch, type ComputedRef, type CSSProperties, type Ref } from 'vue';

type SharedElementRect = {
  top: number;
  left: number;
  width: number;
  height: number;
};

type UseSharedElementHoverOptions = {
  isOpen: ComputedRef<boolean>;
  panelRef: Ref<HTMLElement | null>;
  triggerRef: Ref<HTMLElement | null>;
  x: ComputedRef<number>;
  y: ComputedRef<number>;
};

type SharedElementPhase = 'idle' | 'entering' | 'open' | 'leaving';

const CLOSE_DURATION_MS = 150;
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

const toSharedElementRect = (rect: DOMRect): SharedElementRect => ({
  top: rect.top,
  left: rect.left,
  width: rect.width,
  height: rect.height,
});

const readPreferredReducedMotion = (): boolean => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia(REDUCED_MOTION_QUERY).matches;
};

export const useSharedElementHover = ({
  isOpen,
  panelRef,
  triggerRef,
  x,
  y,
}: UseSharedElementHoverOptions) => {
  const sourceRect = ref<SharedElementRect | null>(null);
  const panelRect = ref<SharedElementRect | null>(null);
  const phase = ref<SharedElementPhase>('idle');
  const prefersReducedMotion = ref(readPreferredReducedMotion());
  let animationFrameId: number | null = null;
  let closeTimeoutId: ReturnType<typeof setTimeout> | null = null;
  let reducedMotionQuery: MediaQueryList | null = null;
  let handleReducedMotionChange: ((event: MediaQueryListEvent) => void) | null = null;

  const clearAnimationFrame = (): void => {
    if (animationFrameId === null) {
      return;
    }
    window.cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  };

  const clearCloseTimeout = (): void => {
    if (closeTimeoutId === null) {
      return;
    }
    clearTimeout(closeTimeoutId);
    closeTimeoutId = null;
  };

  const measurePanel = (): void => {
    const panel = panelRef.value;
    if (!panel) {
      panelRect.value = null;
      return;
    }
    panelRect.value = toSharedElementRect(panel.getBoundingClientRect());
  };

  const beginOpen = async (): Promise<void> => {
    clearAnimationFrame();
    clearCloseTimeout();

    const trigger = triggerRef.value;
    if (!trigger) {
      phase.value = 'open';
      sourceRect.value = null;
      panelRect.value = null;
      return;
    }

    sourceRect.value = toSharedElementRect(trigger.getBoundingClientRect());
    phase.value = prefersReducedMotion.value ? 'open' : 'entering';

    await nextTick();
    measurePanel();

    if (prefersReducedMotion.value) {
      return;
    }

    animationFrameId = window.requestAnimationFrame(() => {
      animationFrameId = null;
      measurePanel();
      phase.value = 'open';
    });
  };

  const beginClose = (): void => {
    clearAnimationFrame();

    if (prefersReducedMotion.value || phase.value === 'idle') {
      phase.value = 'idle';
      return;
    }

    const trigger = triggerRef.value;
    if (trigger) {
      sourceRect.value = toSharedElementRect(trigger.getBoundingClientRect());
    }
    measurePanel();
    phase.value = 'leaving';
    clearCloseTimeout();
    closeTimeoutId = setTimeout(() => {
      closeTimeoutId = null;
      phase.value = 'idle';
      panelRect.value = null;
      sourceRect.value = null;
    }, CLOSE_DURATION_MS);
  };

  const transform = computed(() => {
    if (prefersReducedMotion.value || phase.value === 'open') {
      return 'translate3d(0, 0, 0) scale(1)';
    }

    const source = sourceRect.value;
    const panel = panelRect.value;
    if (!source || !panel || panel.width <= 0 || panel.height <= 0) {
      return 'translate3d(0, 0, 0) scale(0.98)';
    }

    return [
      `translate3d(${source.left - x.value}px, ${source.top - y.value}px, 0)`,
      `scale(${source.width / panel.width}, ${source.height / panel.height})`,
    ].join(' ');
  });

  const overlayStyle = computed<CSSProperties>(() => ({
    left: `${x.value}px`,
    position: 'fixed',
    top: `${y.value}px`,
    transform: transform.value,
    transformOrigin: 'top left',
  }));

  const overlayClass = computed(() => [
    'shared-element-hover-panel',
    phase.value === 'open' ? 'shared-element-hover-panel-open' : '',
    phase.value === 'leaving' ? 'shared-element-hover-panel-leaving' : '',
    prefersReducedMotion.value ? 'shared-element-hover-panel-reduced-motion' : '',
  ]);

  const isMounted = computed(() => isOpen.value || phase.value === 'leaving');
  const revealDetails = computed(() => prefersReducedMotion.value || phase.value === 'open');

  watch(
    isOpen,
    (open) => {
      if (open) {
        void beginOpen();
        return;
      }
      beginClose();
    },
    { flush: 'post' },
  );

  watch([x, y], () => {
    if (isMounted.value) {
      measurePanel();
    }
  });

  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    reducedMotionQuery = window.matchMedia(REDUCED_MOTION_QUERY);
    handleReducedMotionChange = (event: MediaQueryListEvent): void => {
      prefersReducedMotion.value = event.matches;
    };
    reducedMotionQuery.addEventListener?.('change', handleReducedMotionChange);
  }

  onBeforeUnmount(() => {
    clearAnimationFrame();
    clearCloseTimeout();
    if (reducedMotionQuery && handleReducedMotionChange) {
      reducedMotionQuery.removeEventListener?.('change', handleReducedMotionChange);
    }
  });

  return {
    isMounted,
    overlayClass,
    overlayStyle,
    revealDetails,
  };
};
