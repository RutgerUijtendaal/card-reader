import { describe, expect, test } from 'vitest';
import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import {
  buildAdminCardMergeLocation,
  buildAdminCardMergeSourceLocation,
  buildAdminCardDetailLocation,
  buildAdminQuery,
  buildAdminReturnLocation,
  isAdminReturnQuery,
  parseAdminCatalogKind,
  parseAdminEntryId,
  parseAdminMergeSourceId,
  parseAdminMergeTargetId,
  parseAdminTab,
} from '@/composables/admin/adminRouteState';

describe('adminRouteState', () => {
  test('parses admin tab, catalog kind, and entry id from query', () => {
    const query = {
      admin_tab: 'card-groups',
      admin_kind: 'tags',
      admin_entry: 'tag-123',
    };

    expect(parseAdminTab(query, { allowUsers: true, allowMaintenance: true })).toBe('card-groups');
    expect(parseAdminCatalogKind(query)).toBe('tags');
    expect(parseAdminEntryId(query)).toBe('tag-123');
  });

  test('falls back when users tab is not allowed', () => {
    expect(
      parseAdminTab(
        { admin_tab: 'users' },
        { allowUsers: false, allowMaintenance: true },
      ),
    ).toBe('catalog');
  });

  test('builds card detail location that preserves admin context', () => {
    const location = buildAdminCardDetailLocation('card-1', {
      admin_tab: 'catalog',
      admin_kind: 'tags',
      admin_entry: 'tag-123',
    });

    expect(location).toEqual({
      path: '/cards/card-1/edit',
      query: {
        admin_tab: 'catalog',
        admin_kind: 'tags',
        admin_entry: 'tag-123',
        return_to: 'admin',
      },
    });
  });

  test('builds card merge location with a preselected target', () => {
    const location = buildAdminCardMergeLocation('card-1', {
      admin_tab: 'catalog',
    });

    expect(location).toEqual({
      path: '/admin',
      query: {
        admin_tab: 'card-merges',
        admin_merge_target: 'card-1',
      },
    });
    expect(parseAdminMergeTargetId(((location as Exclude<RouteLocationRaw, string>).query ?? {}) as LocationQuery)).toBe('card-1');
  });

  test('builds card merge location with a preselected source', () => {
    const location = buildAdminCardMergeSourceLocation('card-1', {
      admin_tab: 'catalog',
    });

    expect(location).toEqual({
      path: '/admin',
      query: {
        admin_tab: 'card-merges',
        admin_merge_source: 'card-1',
      },
    });
    expect(parseAdminMergeSourceId(((location as Exclude<RouteLocationRaw, string>).query ?? {}) as LocationQuery)).toBe('card-1');
  });

  test('builds admin return location by dropping return_to only', () => {
    const query = {
      admin_tab: 'catalog',
      admin_kind: 'tags',
      admin_entry: 'tag-123',
      return_to: 'admin',
    };

    expect(isAdminReturnQuery(query)).toBe(true);
    expect(buildAdminReturnLocation(query)).toEqual({
      path: '/admin',
      query: {
        admin_tab: 'catalog',
        admin_kind: 'tags',
        admin_entry: 'tag-123',
      },
    });
  });

  test('buildAdminQuery updates only the provided admin keys', () => {
    expect(
      buildAdminQuery(
        {
          foo: 'bar',
          admin_tab: 'catalog',
          admin_kind: 'keywords',
          admin_entry: 'keyword-1',
        },
        {
          kind: 'types',
          entryId: null,
        },
      ),
    ).toEqual({
      foo: 'bar',
      admin_tab: 'catalog',
      admin_kind: 'types',
    });
  });
});
