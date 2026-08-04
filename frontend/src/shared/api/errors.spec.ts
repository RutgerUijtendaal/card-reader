import { describe, expect, test } from 'vitest';
import { getApiErrorDetail, getApiErrorMessage } from '@/shared/api/errors';

describe('API error helpers', () => {
  test('extracts non-empty API detail messages', () => {
    const error = { response: { data: { detail: 'Request failed.' } } };

    expect(getApiErrorDetail(error)).toBe('Request failed.');
    expect(getApiErrorMessage(error, 'Fallback')).toBe('Request failed.');
  });

  test('falls back for missing or blank API detail messages', () => {
    expect(getApiErrorDetail({ response: { data: { detail: '   ' } } })).toBeNull();
    expect(getApiErrorMessage(new Error('Network failed'), 'Fallback')).toBe('Fallback');
  });

  test('includes generic Error messages only when requested', () => {
    expect(
      getApiErrorMessage(new Error('Network failed'), 'Fallback', { includeErrorMessage: true }),
    ).toBe('Network failed');
  });
});
