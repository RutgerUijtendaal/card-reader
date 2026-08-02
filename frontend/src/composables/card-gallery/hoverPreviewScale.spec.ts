import { describe, expect, test } from 'vitest';
import {
  getHoverPreviewCardWidthRem,
  normalizeHoverPreviewScale,
} from '@/composables/card-gallery/hoverPreviewScale';

describe('hoverPreviewScale', () => {
  test('maps the normalized global scale to the shared card preview width', () => {
    expect(getHoverPreviewCardWidthRem(0.8)).toBe(22.4);
    expect(getHoverPreviewCardWidthRem(1)).toBe(28);
    expect(getHoverPreviewCardWidthRem(1.2)).toBe(33.6);
  });

  test('normalizes invalid and out-of-range values before calculating width', () => {
    expect(normalizeHoverPreviewScale('invalid')).toBe(1);
    expect(getHoverPreviewCardWidthRem('invalid')).toBe(28);
    expect(getHoverPreviewCardWidthRem(0.2)).toBe(22.4);
    expect(getHoverPreviewCardWidthRem(2)).toBe(33.6);
  });
});
