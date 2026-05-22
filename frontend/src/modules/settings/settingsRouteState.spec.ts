import { describe, expect, test } from 'vitest';
import {
  buildSettingsCardDetailLocation,
  buildSettingsQuery,
  buildSettingsReturnLocation,
  isSettingsReturnQuery,
  parseSettingsCatalogKind,
  parseSettingsEntryId,
  parseSettingsTab,
} from '@/modules/settings/settingsRouteState';

describe('settingsRouteState', () => {
  test('parses settings tab, catalog kind, and entry id from query', () => {
    const query = {
      settings_tab: 'card-groups',
      settings_kind: 'tags',
      settings_entry: 'tag-123',
    };

    expect(parseSettingsTab(query, { allowUsers: true, allowMaintenance: true })).toBe('card-groups');
    expect(parseSettingsCatalogKind(query)).toBe('tags');
    expect(parseSettingsEntryId(query)).toBe('tag-123');
  });

  test('falls back when users tab is not allowed', () => {
    expect(
      parseSettingsTab(
        { settings_tab: 'users' },
        { allowUsers: false, allowMaintenance: true },
      ),
    ).toBe('catalog');
  });

  test('builds card detail location that preserves settings context', () => {
    const location = buildSettingsCardDetailLocation('card-1', {
      settings_tab: 'catalog',
      settings_kind: 'tags',
      settings_entry: 'tag-123',
    });

    expect(location).toEqual({
      path: '/cards/card-1/edit',
      query: {
        settings_tab: 'catalog',
        settings_kind: 'tags',
        settings_entry: 'tag-123',
        return_to: 'settings',
      },
    });
  });

  test('builds settings return location by dropping return_to only', () => {
    const query = {
      settings_tab: 'catalog',
      settings_kind: 'tags',
      settings_entry: 'tag-123',
      return_to: 'settings',
    };

    expect(isSettingsReturnQuery(query)).toBe(true);
    expect(buildSettingsReturnLocation(query)).toEqual({
      path: '/settings',
      query: {
        settings_tab: 'catalog',
        settings_kind: 'tags',
        settings_entry: 'tag-123',
      },
    });
  });

  test('buildSettingsQuery updates only the provided settings keys', () => {
    expect(
      buildSettingsQuery(
        {
          foo: 'bar',
          settings_tab: 'catalog',
          settings_kind: 'keywords',
          settings_entry: 'keyword-1',
        },
        {
          kind: 'types',
          entryId: null,
        },
      ),
    ).toEqual({
      foo: 'bar',
      settings_tab: 'catalog',
      settings_kind: 'types',
    });
  });
});
