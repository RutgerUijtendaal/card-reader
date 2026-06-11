import { useEventListener } from '@vueuse/core';
import { toValue, watchEffect, type MaybeRefOrGetter, type Ref } from 'vue';
import type { HoverMode } from '@/composables/card-gallery/hoverMode';
import { isEditableKeyboardTarget } from '@/utils/keyboard';

type SearchTargetResolver = () => HTMLInputElement | null;

type GlobalNavigationHotkey = {
  sequence: readonly [prefix: string, key: string];
  enabled: boolean;
  onTrigger: () => void;
};

type HoverModeHotkeyActions = {
  setHoverMode: (mode: HoverMode) => void;
  clearHoverMode: () => void;
};

const primarySearchTargetResolvers: SearchTargetResolver[] = [];
const MAC_PLATFORM_PATTERN = /(Mac|iPhone|iPad|iPod)/i;
const NAVIGATION_SEQUENCE_TIMEOUT_MS = 1500;
let pendingNavigationPrefix: string | null = null;
let pendingNavigationPrefixTimeout: ReturnType<typeof setTimeout> | null = null;

const getPlatform = (): string => globalThis.navigator?.platform ?? '';

const matchesSearchTarget = (element: HTMLInputElement | null): element is HTMLInputElement =>
  element instanceof HTMLInputElement && element.isConnected && !element.disabled;

const getPrimarySearchTarget = (): HTMLInputElement | null => {
  for (let index = primarySearchTargetResolvers.length - 1; index >= 0; index -= 1) {
    const candidate = primarySearchTargetResolvers[index]?.();
    if (matchesSearchTarget(candidate)) {
      return candidate;
    }
  }

  return null;
};

export const isMacLikePlatform = (platform = getPlatform()): boolean => MAC_PLATFORM_PATTERN.test(platform);

export const getModifierKeyLabel = (platform = getPlatform()): 'Cmd' | 'Ctrl' =>
  isMacLikePlatform(platform) ? 'Cmd' : 'Ctrl';

export const getSearchHotkeyLabel = (platform = getPlatform()): string => `${getModifierKeyLabel(platform)}+K`;

export const registerPrimarySearchTarget = (resolver: SearchTargetResolver): (() => void) => {
  primarySearchTargetResolvers.push(resolver);

  return () => {
    const index = primarySearchTargetResolvers.indexOf(resolver);
    if (index >= 0) {
      primarySearchTargetResolvers.splice(index, 1);
    }
  };
};

export const focusPrimarySearchTarget = (): boolean => {
  const target = getPrimarySearchTarget();
  if (!target) {
    return false;
  }

  target.focus();
  target.select();
  return document.activeElement === target;
};

export const handlePrimarySearchHotkey = (event: KeyboardEvent): boolean => {
  if (isEditableKeyboardTarget(event)) {
    return false;
  }

  const focusTriggeredBySlash =
    event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey;
  const focusTriggeredByCommand =
    event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey) && !event.altKey;

  if (!focusTriggeredBySlash && !focusTriggeredByCommand) {
    return false;
  }

  if (!focusPrimarySearchTarget()) {
    return false;
  }

  event.preventDefault();
  return true;
};

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

  const isKnownPrefix = hotkeys.some((hotkey) => hotkey.sequence[0] === normalizedKey);
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
    actions.clearHoverMode();
    return true;
  }
  if (normalizedKey === '3') {
    event.preventDefault();
    actions.setHoverMode('enlarged');
    return true;
  }
  if (normalizedKey === '4') {
    event.preventDefault();
    actions.setHoverMode('enlarged-details');
    return true;
  }

  return false;
};

export const usePrimarySearchTarget = (
  target: Ref<HTMLInputElement | null>,
  enabled: MaybeRefOrGetter<boolean> = true,
): void => {
  watchEffect((onCleanup) => {
    if (!toValue(enabled)) {
      return;
    }

    const unregister = registerPrimarySearchTarget(() => target.value);
    onCleanup(unregister);
  });
};

export const usePrimarySearchHotkeys = (): void => {
  if (typeof window === 'undefined') {
    return;
  }

  useEventListener(window, 'keydown', (event) => {
    handlePrimarySearchHotkey(event);
  });
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
