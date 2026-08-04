import { useEventListener } from '@vueuse/core';
import { toValue, type MaybeRefOrGetter } from 'vue';
import type { HoverMode } from '@/domain/cards/utils/gallery/hoverMode';
import { isEditableKeyboardTarget } from '@/shared/utils/keyboard';

type GlobalNavigationHotkey = {
  sequence: readonly [prefix: string, key: string];
  enabled: boolean;
  onTrigger: () => void;
};

type HoverModeHotkeyActions = {
  setHoverMode: (mode: HoverMode) => void;
  clearHoverMode: () => void;
};

const NAVIGATION_SEQUENCE_TIMEOUT_MS = 1500;
let pendingNavigationPrefix: string | null = null;
let pendingNavigationPrefixTimeout: ReturnType<typeof setTimeout> | null = null;

const clearPendingNavigationPrefix = (): void => {
  pendingNavigationPrefix = null;
  if (pendingNavigationPrefixTimeout !== null) {
    clearTimeout(pendingNavigationPrefixTimeout);
    pendingNavigationPrefixTimeout = null;
  }
};

export const resetHotkeyStateForTests = (): void => {
  clearPendingNavigationPrefix();
};

const startPendingNavigationPrefix = (prefix: string): void => {
  clearPendingNavigationPrefix();
  pendingNavigationPrefix = prefix;
  pendingNavigationPrefixTimeout = setTimeout(() => {
    clearPendingNavigationPrefix();
  }, NAVIGATION_SEQUENCE_TIMEOUT_MS);
};

const getNormalizedNavigationKey = (event: KeyboardEvent): string | null => {
  if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || event.key.length !== 1) {
    return null;
  }

  return event.key.toLowerCase();
};

export const handleGlobalNavigationHotkey = (
  event: KeyboardEvent,
  hotkeys: readonly GlobalNavigationHotkey[],
): boolean => {
  if (isEditableKeyboardTarget(event)) {
    clearPendingNavigationPrefix();
    return false;
  }

  if (event.key === 'Escape') {
    clearPendingNavigationPrefix();
    return false;
  }

  const normalizedKey = getNormalizedNavigationKey(event);
  if (normalizedKey === null) {
    clearPendingNavigationPrefix();
    return false;
  }

  if (pendingNavigationPrefix !== null) {
    const matchedAction = hotkeys.find(
      (hotkey) =>
        hotkey.enabled &&
        hotkey.sequence[0] === pendingNavigationPrefix &&
        hotkey.sequence[1] === normalizedKey,
    );

    clearPendingNavigationPrefix();
    if (matchedAction) {
      event.preventDefault();
      matchedAction.onTrigger();
      return true;
    }
  }

  const isKnownPrefix = hotkeys.some((hotkey) => hotkey.enabled && hotkey.sequence[0] === normalizedKey);
  if (isKnownPrefix) {
    startPendingNavigationPrefix(normalizedKey);
  }

  return false;
};

export const handleHoverModeHotkey = (
  event: KeyboardEvent,
  actions: HoverModeHotkeyActions | null,
): boolean => {
  if (!actions || isEditableKeyboardTarget(event)) {
    return false;
  }

  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return false;
  }

  const normalizedKey = event.key.toLowerCase();
  if (normalizedKey === '1') {
    event.preventDefault();
    actions.setHoverMode('none');
    return true;
  }
  if (normalizedKey === '2') {
    event.preventDefault();
    actions.setHoverMode('enlarged');
    return true;
  }
  if (normalizedKey === '3') {
    event.preventDefault();
    actions.setHoverMode('details');
    return true;
  }
  if (normalizedKey === '4') {
    event.preventDefault();
    actions.setHoverMode('enlarged-details');
    return true;
  }
  if (normalizedKey === '5') {
    event.preventDefault();
    actions.clearHoverMode();
    return true;
  }

  return false;
};

export const useGlobalNavigationHotkeys = (
  hotkeys: MaybeRefOrGetter<readonly GlobalNavigationHotkey[]>,
): void => {
  if (typeof window === 'undefined') {
    return;
  }

  useEventListener(window, 'keydown', (event) => {
    handleGlobalNavigationHotkey(event, toValue(hotkeys));
  });
};

export const useHoverModeHotkeys = (
  actions: MaybeRefOrGetter<HoverModeHotkeyActions | null>,
): void => {
  if (typeof window === 'undefined') {
    return;
  }

  useEventListener(window, 'keydown', (event) => {
    handleHoverModeHotkey(event, toValue(actions));
  });
};
