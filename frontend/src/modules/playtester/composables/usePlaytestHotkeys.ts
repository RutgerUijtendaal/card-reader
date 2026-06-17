import type { ComputedRef } from 'vue';
import { useEventListener } from '@vueuse/core';
import { isEditableKeyboardTarget } from '@/utils/keyboard';

type UsePlaytestHotkeysOptions = {
  enabled: ComputedRef<boolean>;
  handleHotkey: (event: KeyboardEvent) => boolean;
};

export const usePlaytestHotkeys = ({
  enabled,
  handleHotkey,
}: UsePlaytestHotkeysOptions): void => {
  useEventListener(window, 'keydown', (event) => {
    if (!enabled.value || isEditableKeyboardTarget(event)) {
      return;
    }
    if (handleHotkey(event)) {
      event.preventDefault();
    }
  });
};
