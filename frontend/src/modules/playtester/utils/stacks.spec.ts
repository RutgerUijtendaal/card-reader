import { describe, expect, test } from 'vitest';
import {
  getCollapsedStackZoneIds,
  PLAYTEST_STACK_OPENING_BUDGET_RATIO,
  PLAYTEST_STACK_PLAY_BUDGET_RATIO,
} from '@/modules/playtester/utils/stacks';

describe('playtester stack collapse sizing', () => {
  test('setup collapses stacks earlier than the main play view', () => {
    const playCollapsed = getCollapsedStackZoneIds(1300, 0.75, 16, PLAYTEST_STACK_PLAY_BUDGET_RATIO);
    const openingCollapsed = getCollapsedStackZoneIds(1300, 0.75, 16, PLAYTEST_STACK_OPENING_BUDGET_RATIO);

    expect(playCollapsed.size).toBe(0);
    expect(openingCollapsed.has('hero')).toBe(true);
    expect(openingCollapsed.size).toBeGreaterThan(playCollapsed.size);
  });
});
