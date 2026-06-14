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

  it('excludes mana-type cards from totals and buckets', () => {
    const summary = buildManaCurve([
      { quantity: 3, card: { mana_value: 0, types: [{ key: 'mana' }] } },
      { quantity: 2, card: { mana_value: 2, types: [{ key: 'spell' }] } },
    ]);

    expect(summary.totalCards).toBe(2);
    expect(summary.excludedManaCards).toBe(3);
    expect(summary.buckets.map((bucket) => ({ label: bucket.label, count: bucket.count }))).toEqual([
      { label: '1', count: 0 },
      { label: '2', count: 2 },
      { label: '3', count: 0 },
      { label: '4', count: 0 },
      { label: '5', count: 0 },
      { label: '6', count: 0 },
      { label: '7+', count: 0 },
    ]);
  });

  it('keeps the zero bucket when a non-mana card costs zero', () => {
    const summary = buildManaCurve([
      { quantity: 1, card: { mana_value: 0, types: [{ key: 'artifact' }] } },
      { quantity: 2, card: { mana_value: 1, types: [{ key: 'spell' }] } },
    ]);

    expect(summary.buckets.map((bucket) => ({ label: bucket.label, count: bucket.count }))).toEqual([
      { label: '0', count: 1 },
      { label: '1', count: 2 },
      { label: '2', count: 0 },
      { label: '3', count: 0 },
      { label: '4', count: 0 },
      { label: '5', count: 0 },
      { label: '6', count: 0 },
      { label: '7+', count: 0 },
    ]);
  });

  it('starts at one when no non-mana cards cost zero', () => {
    const summary = buildManaCurve([
      { quantity: 1, card: { mana_value: 1, types: [{ key: 'spell' }] } },
      { quantity: 2, card: { mana_value: 3, types: [{ key: 'creature' }] } },
    ]);

    expect(summary.buckets[0]?.label).toBe('1');
    expect(summary.buckets.some((bucket) => bucket.label === '0')).toBe(false);
  });

  it('reports all-mana inputs as excluded with no visible curve counts', () => {
    const summary = buildManaCurve([
      { quantity: 2, card: { mana_value: 0, types: [{ key: 'Mana' }] } },
      { quantity: 1, card: { mana_value: 0, types: [{ key: ' mana ' }] } },
    ]);

    expect(summary.totalCards).toBe(0);
    expect(summary.uncostedCards).toBe(0);
    expect(summary.excludedManaCards).toBe(3);
    expect(summary.maxBucketCount).toBe(0);
    expect(summary.buckets.every((bucket) => bucket.count === 0)).toBe(true);
  });
});
