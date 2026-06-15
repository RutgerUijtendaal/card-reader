import { afterEach, describe, expect, test, vi } from 'vitest';
import {
  getModifierKeyLabel,
  handleGlobalNavigationHotkey,
  handleHoverModeHotkey,
  handlePrimarySearchHotkey,
  registerPrimarySearchTarget,
  resetHotkeyStateForTests,
} from '@/composables/useHotkeys';

describe('useHotkeys', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    resetHotkeyStateForTests();
  });

  test('slash focuses the registered primary search input', () => {
    const input = document.createElement('input');
    document.body.appendChild(input);
    const unregister = registerPrimarySearchTarget(() => input);

    const event = new KeyboardEvent('keydown', {
      key: '/',
      cancelable: true,
    });

    expect(handlePrimarySearchHotkey(event)).toBe(true);
    expect(document.activeElement).toBe(input);
    expect(event.defaultPrevented).toBe(true);

    unregister();
  });

  test('command search shortcut focuses the registered primary search input', () => {
    const input = document.createElement('input');
    document.body.appendChild(input);
    const unregister = registerPrimarySearchTarget(() => input);

    const event = new KeyboardEvent('keydown', {
      key: 'k',
      ctrlKey: true,
      cancelable: true,
    });

    expect(handlePrimarySearchHotkey(event)).toBe(true);
    expect(document.activeElement).toBe(input);
    expect(event.defaultPrevented).toBe(true);

    unregister();
  });

  test('search shortcuts do nothing from editable fields', () => {
    const input = document.createElement('input');
    const textarea = document.createElement('textarea');
    document.body.append(input, textarea);
    const unregister = registerPrimarySearchTarget(() => input);

    const event = new KeyboardEvent('keydown', {
      key: '/',
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      configurable: true,
      value: textarea,
    });

    expect(handlePrimarySearchHotkey(event)).toBe(false);
    expect(document.activeElement).not.toBe(input);
    expect(event.defaultPrevented).toBe(false);

    unregister();
  });

  test('global navigation sequences trigger only when enabled', () => {
    const onTrigger = vi.fn();
    const disabledPrefixEvent = new KeyboardEvent('keydown', {
      key: 'n',
      cancelable: true,
    });
    const disabledActionEvent = new KeyboardEvent('keydown', {
      key: 'n',
      cancelable: true,
    });

    expect(
      handleGlobalNavigationHotkey(disabledPrefixEvent, [
        { sequence: ['n', 'n'], enabled: false, onTrigger },
      ]),
    ).toBe(false);
    expect(
      handleGlobalNavigationHotkey(disabledActionEvent, [
        { sequence: ['n', 'n'], enabled: false, onTrigger },
      ]),
    ).toBe(false);
    expect(onTrigger).not.toHaveBeenCalled();
    resetHotkeyStateForTests();

    const prefixEvent = new KeyboardEvent('keydown', {
      key: 'n',
      cancelable: true,
    });
    const actionEvent = new KeyboardEvent('keydown', {
      key: 'n',
      cancelable: true,
    });

    expect(
      handleGlobalNavigationHotkey(prefixEvent, [
        { sequence: ['n', 'n'], enabled: true, onTrigger },
      ]),
    ).toBe(false);
    expect(
      handleGlobalNavigationHotkey(actionEvent, [
        { sequence: ['n', 'n'], enabled: true, onTrigger },
      ]),
    ).toBe(true);
    expect(onTrigger).toHaveBeenCalledOnce();
    expect(actionEvent.defaultPrevented).toBe(true);
  });

  test('disabled global navigation prefixes are not remembered for later enabled actions', () => {
    const onTrigger = vi.fn();
    const disabledPrefixEvent = new KeyboardEvent('keydown', {
      key: 'n',
      cancelable: true,
    });
    const enabledActionEvent = new KeyboardEvent('keydown', {
      key: 'n',
      cancelable: true,
    });

    expect(
      handleGlobalNavigationHotkey(disabledPrefixEvent, [
        { sequence: ['n', 'n'], enabled: false, onTrigger },
      ]),
    ).toBe(false);
    expect(
      handleGlobalNavigationHotkey(enabledActionEvent, [
        { sequence: ['n', 'n'], enabled: true, onTrigger },
      ]),
    ).toBe(false);
    expect(onTrigger).not.toHaveBeenCalled();
    expect(enabledActionEvent.defaultPrevented).toBe(false);
  });

  test('global navigation sequences do nothing from editable fields', () => {
    const onTrigger = vi.fn();
    const input = document.createElement('input');
    document.body.appendChild(input);

    const event = new KeyboardEvent('keydown', {
      key: 'g',
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      configurable: true,
      value: input,
    });

    expect(
      handleGlobalNavigationHotkey(event, [
        { sequence: ['n', 'n'], enabled: true, onTrigger },
      ]),
    ).toBe(false);
    expect(onTrigger).not.toHaveBeenCalled();
  });

  test('hover mode hotkeys trigger the mapped actions', () => {
    const setHoverMode = vi.fn();
    const clearHoverMode = vi.fn();
    const actions = { setHoverMode, clearHoverMode };

    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '1', altKey: true, cancelable: true }), actions))
      .toBe(true);
    expect(setHoverMode).toHaveBeenLastCalledWith('none');

    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '2', altKey: true, cancelable: true }), actions))
      .toBe(true);
    expect(setHoverMode).toHaveBeenLastCalledWith('enlarged');

    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '3', altKey: true, cancelable: true }), actions))
      .toBe(true);
    expect(setHoverMode).toHaveBeenLastCalledWith('details');

    const cardDetailsEvent = new KeyboardEvent('keydown', { key: '4', altKey: true, cancelable: true });
    expect(handleHoverModeHotkey(cardDetailsEvent, actions)).toBe(true);
    expect(setHoverMode).toHaveBeenLastCalledWith('enlarged-details');
    expect(cardDetailsEvent.defaultPrevented).toBe(true);

    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '5', altKey: true, cancelable: true }), actions))
      .toBe(true);
    expect(clearHoverMode).toHaveBeenCalledOnce();
  });

  test('hover mode hotkeys do nothing from editable fields', () => {
    const setHoverMode = vi.fn();
    const input = document.createElement('input');
    document.body.appendChild(input);
    const event = new KeyboardEvent('keydown', {
      key: '1',
      altKey: true,
      cancelable: true,
    });
    Object.defineProperty(event, 'target', {
      configurable: true,
      value: input,
    });

    expect(handleHoverModeHotkey(event, { setHoverMode, clearHoverMode: vi.fn() })).toBe(false);
    expect(setHoverMode).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);
  });

  test('hover mode hotkeys ignore unrelated modifiers and keys', () => {
    const setHoverMode = vi.fn();
    const clearHoverMode = vi.fn();
    const actions = { setHoverMode, clearHoverMode };

    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '1', cancelable: true }), actions)).toBe(false);
    expect(
      handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '1', altKey: true, shiftKey: true, cancelable: true }), actions),
    ).toBe(false);
    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '6', altKey: true, cancelable: true }), actions))
      .toBe(false);
    expect(handleHoverModeHotkey(new KeyboardEvent('keydown', { key: '1', altKey: true, cancelable: true }), null))
      .toBe(false);
    expect(setHoverMode).not.toHaveBeenCalled();
    expect(clearHoverMode).not.toHaveBeenCalled();
  });

  test('modifier labels resolve by platform', () => {
    expect(getModifierKeyLabel('MacIntel')).toBe('Cmd');
    expect(getModifierKeyLabel('Win32')).toBe('Ctrl');
  });
});
