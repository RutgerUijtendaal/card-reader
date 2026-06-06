import { describe, expect, it } from 'vitest';
import { buildManaCurve } from '@/composables/decks/manaCurve';

describe('buildManaCurve', () => {
  it('counts cards by mana value and caps the overflow bucket', () => {
    const summary = buildManaCurve([
      { quantity: 2, card: { mana_value: 1 } },
      { quantity: 3, card: { mana_value: 4 } },
      { quantity: 1, card: { mana_value: 7 } },
      { quantity: 2, card: { mana_value: 10 } },
    ]);

    expect(summary.totalCards).toBe(8);
    expect(summary.uncostedCards).toBe(0);
    expect(summary.maxBucketCount).toBe(3);
    expect(summary.buckets.map((bucket) => ({ label: bucket.label, count: bucket.count }))).toEqual([
      { label: '0', count: 0 },
      { label: '1', count: 2 },
      { label: '2', count: 0 },
      { label: '3', count: 0 },
      { label: '4', count: 3 },
      { label: '5', count: 0 },
      { label: '6', count: 0 },
      { label: '7+', count: 3 },
    ]);
    expect(summary.buckets.find((bucket) => bucket.label === '4')?.heightRatio).toBe(1);
  });

  it('tracks cards without a usable mana value separately', () => {
    const summary = buildManaCurve([
      { quantity: 1, card: { mana_value: null } },
      { quantity: 2, card: { mana_value: -1 } },
      { quantity: 3, card: { mana_value: 2 } },
    ]);

    expect(summary.totalCards).toBe(6);
    expect(summary.uncostedCards).toBe(3);
    expect(summary.buckets.find((bucket) => bucket.label === '2')?.count).toBe(3);
  });
});
