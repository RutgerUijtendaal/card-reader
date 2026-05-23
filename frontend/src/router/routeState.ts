import type { LocationQuery, LocationQueryRaw } from 'vue-router';

export const queryString = (value: unknown): string | null =>
  typeof value === 'string' && value.trim().length > 0 ? value : null;

export const mergeLocationQuery = (
  query: LocationQuery,
  updates: Record<string, string | null | undefined>,
): LocationQueryRaw => {
  const nextQuery: LocationQueryRaw = { ...query };

  Object.entries(updates).forEach(([key, value]) => {
    if (value) {
      nextQuery[key] = value;
      return;
    }
    delete nextQuery[key];
  });

  return nextQuery;
};

export const addReturnToQuery = (
  query: LocationQuery,
  returnTo: string,
  extra: Record<string, string | null | undefined> = {},
): LocationQueryRaw =>
  mergeLocationQuery(query, {
    ...extra,
    return_to: returnTo,
  });

export const clearLocationQueryKeys = (
  query: LocationQuery,
  keys: readonly string[],
): LocationQueryRaw => {
  const nextQuery: LocationQueryRaw = { ...query };
  keys.forEach((key) => {
    delete nextQuery[key];
  });
  return nextQuery;
};
