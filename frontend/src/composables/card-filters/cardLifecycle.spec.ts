import { describe, expect, test } from 'vitest';
import {
  buildCardLifecycleApiParams,
  cardIsDeprecated,
  managementCardSearchLifecycleParams,
  normalizeCardLifecycleFilterValue,
  normalizeCardLifecycleStatus,
} from './cardLifecycle';

describe('cardLifecycle', () => {
  test('centralizes lifecycle filter normalization and API params', () => {
    expect(normalizeCardLifecycleFilterValue('deprecated')).toBe('deprecated');
    expect(normalizeCardLifecycleFilterValue('all')).toBe('all');
    expect(normalizeCardLifecycleFilterValue('unknown')).toBe('active');
    expect(buildCardLifecycleApiParams('active')).toBeUndefined();
    expect(buildCardLifecycleApiParams('all')).toEqual({ lifecycle_status: 'all' });
    expect(managementCardSearchLifecycleParams()).toEqual({ lifecycle_status: 'all' });
  });

  test('centralizes deprecated card status checks', () => {
    expect(normalizeCardLifecycleStatus('unknown')).toBe('active');
    expect(cardIsDeprecated({ lifecycle_status: 'deprecated' })).toBe(true);
    expect(cardIsDeprecated({ lifecycle_status: 'active' })).toBe(false);
    expect(cardIsDeprecated(null)).toBe(false);
  });
});
