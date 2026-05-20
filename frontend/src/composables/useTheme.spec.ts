import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { nextTick } from 'vue';
import {
  __resetThemeForTests,
  applyResolvedTheme,
  initTheme,
  resolveThemePreference,
  useTheme,
} from '@/composables/useTheme';

type MediaListener = (event: MediaQueryListEvent) => void;

const createMatchMedia = (initialMatches: boolean) => {
  let matches = initialMatches;
  const listeners = new Set<MediaListener>();

  const mediaQueryList = {
    get matches() {
      return matches;
    },
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addEventListener: (
      _type: string,
      listener: EventListenerOrEventListenerObject | null,
      options?: boolean | AddEventListenerOptions,
    ) => {
      void options;
      if (typeof listener === 'function') {
        listeners.add(listener as MediaListener);
      }
    },
    removeEventListener: (
      _type: string,
      listener: EventListenerOrEventListenerObject | null,
      options?: boolean | EventListenerOptions,
    ) => {
      void options;
      if (typeof listener === 'function') {
        listeners.delete(listener as MediaListener);
      }
    },
    addListener: (listener: MediaListener) => {
      listeners.add(listener);
    },
    removeListener: (listener: MediaListener) => {
      listeners.delete(listener);
    },
    dispatchEvent: () => {
      return true;
    },
    dispatch(nextMatches: boolean) {
      matches = nextMatches;
      const event = { matches, media: this.media } as MediaQueryListEvent;
      listeners.forEach((listener) => listener(event));
    },
  } satisfies MediaQueryList & {
    dispatch: (matches: boolean) => void;
  };

  return mediaQueryList;
};

describe('useTheme', () => {
  let mediaQueryList: ReturnType<typeof createMatchMedia>;

  beforeEach(() => {
    localStorage.clear();
    mediaQueryList = createMatchMedia(false);
    vi.stubGlobal('matchMedia', vi.fn(() => mediaQueryList));
    __resetThemeForTests();
  });

  afterEach(() => {
    __resetThemeForTests();
    vi.unstubAllGlobals();
  });

  test('defaults to system preference', () => {
    const theme = useTheme();

    expect(theme.preference.value).toBe('system');
    expect(theme.resolvedTheme.value).toBe('light');
  });

  test('light preference forces light mode', async () => {
    const theme = useTheme();
    theme.setPreference('light');
    await nextTick();

    expect(theme.resolvedTheme.value).toBe('light');
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  test('dark preference forces dark mode', async () => {
    const theme = useTheme();
    theme.setPreference('dark');
    await nextTick();

    expect(theme.resolvedTheme.value).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  test('system preference follows matchMedia changes', async () => {
    const theme = useTheme();
    expect(theme.resolvedTheme.value).toBe('light');

    mediaQueryList.dispatch(true);
    await nextTick();

    expect(theme.resolvedTheme.value).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  test('changing preference persists to localStorage', async () => {
    const theme = useTheme();
    theme.setPreference('dark');
    await nextTick();

    expect(localStorage.getItem('card-reader.theme')).toBe('dark');
  });

  test('initTheme applies stored preference before app mount', () => {
    localStorage.setItem('card-reader.theme', 'dark');

    initTheme();

    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  test('resolveThemePreference respects system mode', () => {
    expect(resolveThemePreference('system', true)).toBe('dark');
    expect(resolveThemePreference('system', false)).toBe('light');
    expect(resolveThemePreference('light', true)).toBe('light');
  });

  test('applyResolvedTheme updates root color-scheme', () => {
    applyResolvedTheme('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
    applyResolvedTheme('light');
    expect(document.documentElement.style.colorScheme).toBe('light');
  });
});
