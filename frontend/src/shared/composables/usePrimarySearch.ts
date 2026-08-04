import { useEventListener } from '@vueuse/core';
import { toValue, watchEffect, type MaybeRefOrGetter, type Ref } from 'vue';
import { isEditableKeyboardTarget } from '@/shared/utils/keyboard';

type SearchTargetResolver = () => HTMLInputElement | null;

const primarySearchTargetResolvers: SearchTargetResolver[] = [];
const MAC_PLATFORM_PATTERN = /(Mac|iPhone|iPad|iPod)/i;

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
  if (!target) return false;
  target.focus();
  target.select();
  return document.activeElement === target;
};

export const handlePrimarySearchHotkey = (event: KeyboardEvent): boolean => {
  if (isEditableKeyboardTarget(event)) return false;

  const focusTriggeredBySlash =
    event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.shiftKey;
  const focusTriggeredByCommand =
    event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey) && !event.altKey;
  if (!focusTriggeredBySlash && !focusTriggeredByCommand) return false;
  if (!focusPrimarySearchTarget()) return false;

  event.preventDefault();
  return true;
};

export const usePrimarySearchTarget = (
  target: Readonly<Ref<HTMLInputElement | null>>,
  enabled: MaybeRefOrGetter<boolean> = true,
): void => {
  watchEffect((onCleanup) => {
    if (!toValue(enabled)) return;
    const unregister = registerPrimarySearchTarget(() => target.value);
    onCleanup(unregister);
  });
};

export const usePrimarySearchHotkeys = (
  enabled: MaybeRefOrGetter<boolean> = true,
): void => {
  if (typeof window === 'undefined') return;
  useEventListener(window, 'keydown', (event) => {
    if (toValue(enabled)) {
      handlePrimarySearchHotkey(event);
    }
  });
};
