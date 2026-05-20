import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';
import { useLocalStorage } from '@vueuse/core';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'card-reader.theme';
const DARK_MODE_MEDIA_QUERY = '(prefers-color-scheme: dark)';

type ThemeState = {
  preference: Ref<ThemePreference>;
  resolvedTheme: ComputedRef<ResolvedTheme>;
  setPreference: (value: ThemePreference) => void;
};

let themeState: ThemeState | null = null;
let removeMediaListener: (() => void) | null = null;

const isThemePreference = (value: string | null): value is ThemePreference =>
  value === 'light' || value === 'dark' || value === 'system';

const readStoredPreference = (): ThemePreference => {
  if (typeof window === 'undefined') {
    return 'system';
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isThemePreference(stored) ? stored : 'system';
  } catch {
    return 'system';
  }
};

const getMediaQueryList = (): MediaQueryList | null => {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return null;
  }

  return window.matchMedia(DARK_MODE_MEDIA_QUERY);
};

const readSystemPrefersDark = (): boolean => getMediaQueryList()?.matches ?? false;

export const resolveThemePreference = (
  preference: ThemePreference,
  systemPrefersDark: boolean,
): ResolvedTheme => {
  if (preference === 'system') {
    return systemPrefersDark ? 'dark' : 'light';
  }

  return preference;
};

export const applyResolvedTheme = (theme: ResolvedTheme): void => {
  if (typeof document === 'undefined') {
    return;
  }

  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
};

export const initTheme = (): void => {
  applyResolvedTheme(resolveThemePreference(readStoredPreference(), readSystemPrefersDark()));
};

const ensureThemeState = (): ThemeState => {
  if (themeState) {
    return themeState;
  }

  const preference = useLocalStorage<ThemePreference>(STORAGE_KEY, 'system', {
    mergeDefaults: true,
    writeDefaults: true,
  });
  const systemPrefersDark = ref(readSystemPrefersDark());
  const resolvedTheme = computed<ResolvedTheme>(() =>
    resolveThemePreference(preference.value, systemPrefersDark.value),
  );

  const mediaQueryList = getMediaQueryList();
  if (mediaQueryList) {
    const listener = (event: MediaQueryListEvent): void => {
      systemPrefersDark.value = event.matches;
    };

    mediaQueryList.addEventListener('change', listener);
    removeMediaListener = () => mediaQueryList.removeEventListener('change', listener);
  }

  watch(
    resolvedTheme,
    (value) => {
      applyResolvedTheme(value);
    },
    { immediate: true, flush: 'sync' },
  );

  themeState = {
    preference,
    resolvedTheme,
    setPreference: (value) => {
      preference.value = value;
    },
  };

  return themeState;
};

export const useTheme = (): ThemeState => ensureThemeState();

export const __resetThemeForTests = (): void => {
  removeMediaListener?.();
  removeMediaListener = null;
  themeState = null;
  if (typeof document !== 'undefined') {
    document.documentElement.classList.remove('dark');
    delete document.documentElement.dataset.theme;
    document.documentElement.style.removeProperty('color-scheme');
  }
};
