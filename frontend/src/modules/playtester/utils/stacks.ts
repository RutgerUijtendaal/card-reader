import { DEFAULT_PLAYTEST_STACK_FACES } from '@/modules/playtester/playtestState';
import type {
  PlaytestStackDefinition,
  PlaytestStackFace,
  PlaytestZoneId,
} from '@/modules/playtester/types';

export const PLAYTEST_STACK_DEFINITIONS: PlaytestStackDefinition[] = [
  { id: 'library', label: 'Library', defaultAction: 'draw' },
  { id: 'discard', label: 'Discard', defaultAction: 'open' },
  { id: 'banish', label: 'Banish', defaultAction: 'open' },
  { id: 'hero', label: 'Hero', defaultAction: 'open' },
];

export const PLAYTEST_STACK_COLLAPSE_ORDER: PlaytestZoneId[] = ['hero', 'banish', 'discard', 'library'];

export const getPlaytestStackFace = (
  stackFaces: Partial<Record<PlaytestZoneId, PlaytestStackFace>> | undefined,
  zoneId: PlaytestZoneId,
): PlaytestStackFace =>
  stackFaces?.[zoneId] ?? DEFAULT_PLAYTEST_STACK_FACES[zoneId] ?? 'front';

export const getCollapsedStackZoneIds = (
  lowerBarWidth: number,
  cardScale: number,
  rootFontSize: number,
): Set<PlaytestZoneId> => {
  if (lowerBarWidth <= 0) {
    return new Set();
  }
  const fullWidth = 11.35 * cardScale * rootFontSize;
  const buttonWidth = 3.25 * Math.min(cardScale, 1.12) * rootFontSize;
  const gap = 0.75 * rootFontSize;
  const stackWidthBudget = Math.max((buttonWidth * 4) + (gap * 3), lowerBarWidth * 0.52);
  let collapsedCount = 0;

  for (let count = 0; count <= PLAYTEST_STACK_COLLAPSE_ORDER.length; count += 1) {
    const expandedCount = PLAYTEST_STACK_COLLAPSE_ORDER.length - count;
    const requiredWidth = (expandedCount * fullWidth) + (count * buttonWidth) + (gap * 3);
    if (requiredWidth <= stackWidthBudget) {
      collapsedCount = count;
      break;
    }
    collapsedCount = count;
  }

  return new Set(PLAYTEST_STACK_COLLAPSE_ORDER.slice(0, collapsedCount));
};
