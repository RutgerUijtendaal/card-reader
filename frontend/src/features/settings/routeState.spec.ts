import { describe, expect, test } from 'vitest';
import { buildSettingsTabLocation, parseSettingsTab } from './routeState';

describe('settings route state', () => {
  test('parses a settings tab from the query', () => {
    expect(
      parseSettingsTab(
        { settings_tab: 'hover' },
        { allowDeveloperData: true },
      ),
    ).toBe('hover');
  });

  test('falls back to display for unknown or unavailable tabs', () => {
    expect(
      parseSettingsTab(
        { settings_tab: 'unknown' },
        { allowDeveloperData: true },
      ),
    ).toBe('display');
    expect(
      parseSettingsTab(
        { settings_tab: 'developer-data' },
        { allowDeveloperData: false },
      ),
    ).toBe('display');
  });

  test('builds a settings tab location while preserving unrelated query state', () => {
    expect(
      buildSettingsTabLocation('sort', {
        settings_tab: 'display',
        source: 'notification',
      }),
    ).toEqual({
      path: '/settings',
      query: {
        settings_tab: 'sort',
        source: 'notification',
      },
    });
  });
});
