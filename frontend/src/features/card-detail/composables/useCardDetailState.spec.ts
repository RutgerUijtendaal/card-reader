import { describe, expect, test } from 'vitest';
import type { CardGroupSummary } from '@/domain/cards/types';
import { reconcileCardGroupsAfterPoolChange } from './useCardDetailState';

const buildGroup = (
  id: string,
  cardPool: CardGroupSummary['card_pool'],
  isAnchor: boolean,
): CardGroupSummary => ({
  id,
  key: id,
  name: id,
  card_pool: cardPool,
  anchor_card_id: isAnchor ? 'card-1' : `${id}-anchor`,
  member_count: 2,
  card_ids: ['card-1', `${id}-member`],
  is_anchor: isAnchor,
  position: isAnchor ? 1 : 2,
});

describe('reconcileCardGroupsAfterPoolChange', () => {
  test('updates anchored groups and removes stale groups anchored in the previous pool', () => {
    const groups = [
      buildGroup('anchored-group', 'player', true),
      buildGroup('old-pool-group', 'player', false),
      buildGroup('target-pool-group', 'game_master', false),
    ];

    expect(reconcileCardGroupsAfterPoolChange(groups, 'game_master')).toEqual([
      { ...groups[0], card_pool: 'game_master' },
      groups[2],
    ]);
  });
});
