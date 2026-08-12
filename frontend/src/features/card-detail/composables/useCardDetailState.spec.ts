import { describe, expect, test } from 'vitest';
import type { CardGroupSummary } from '@/domain/cards/types';
import {
  reconcileCardGroupsAfterPoolChange,
  synchronizeCardClassification,
  type CardClassificationFields,
} from './useCardDetailState';

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
      buildGroup('target-pool-group', 'evil', false),
    ];

    expect(reconcileCardGroupsAfterPoolChange(groups, 'evil')).toEqual([
      { ...groups[0], card_pool: 'evil' },
      groups[2],
    ]);
  });
});

describe('synchronizeCardClassification', () => {
  test('updates card-level classification across current and historical generations', () => {
    const generations: CardClassificationFields[] = [
      {
        version_id: 'current',
        card_pool: 'player',
        card_roles: ['hero'],
        deck_building_config: { overrides: {} },
        lifecycle_status: 'active',
      },
      {
        version_id: 'historical',
        card_pool: 'player',
        card_roles: ['hero'],
        deck_building_config: { overrides: {} },
        lifecycle_status: 'active',
      },
    ];
    const updated: CardClassificationFields = {
      ...generations[0],
      card_pool: 'evil',
      card_roles: ['event'],
      deck_building_config: { overrides: { mainboard_copy_limit: { max: 1 } } },
      lifecycle_status: 'deprecated',
    };

    expect(synchronizeCardClassification(generations, updated)).toEqual([
      updated,
      {
        ...generations[1],
        card_pool: 'evil',
        card_roles: ['event'],
        deck_building_config: updated.deck_building_config,
        lifecycle_status: 'deprecated',
      },
    ]);
  });
});
