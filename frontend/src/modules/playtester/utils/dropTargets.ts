import type { PlaytestDraggedCard, PlaytestZoneId } from '@/modules/playtester/types';

export type PlaytestResolvedDropTarget =
  | { type: 'card'; instanceId: string }
  | { type: 'zone'; zoneId: PlaytestZoneId | 'board' };

export const boardDropPosition = (
  board: HTMLElement | null,
  drag: Pick<PlaytestDraggedCard, 'pointerX' | 'pointerY' | 'pointerOffsetX' | 'pointerOffsetY' | 'sourceWidth' | 'sourceHeight'>,
): { x: number; y: number } | null => {
  if (!board) {
    return null;
  }
  const bounds = board.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return null;
  }
  if (drag.pointerX < bounds.left || drag.pointerX > bounds.right || drag.pointerY < bounds.top || drag.pointerY > bounds.bottom) {
    return null;
  }
  const centerX = drag.pointerX - drag.pointerOffsetX + drag.sourceWidth / 2;
  const centerY = drag.pointerY - drag.pointerOffsetY + drag.sourceHeight / 2;
  return {
    x: ((centerX - bounds.left) / bounds.width) * 100,
    y: ((centerY - bounds.top) / bounds.height) * 100,
  };
};

export const resolvePlaytestDropTarget = (
  clientX: number,
  clientY: number,
  draggedInstanceId?: string,
): PlaytestResolvedDropTarget | null => {
  const elements = typeof document.elementsFromPoint === 'function'
    ? document.elementsFromPoint(clientX, clientY)
    : typeof document.elementFromPoint === 'function'
      ? [document.elementFromPoint(clientX, clientY)].filter(Boolean)
      : [];

  for (const element of elements) {
    if (!(element instanceof HTMLElement)) {
      continue;
    }
    const card = element.closest<HTMLElement>('[data-instance-id]');
    if (card?.dataset.instanceId) {
      if (card.dataset.instanceId === draggedInstanceId) {
        continue;
      }
      return { type: 'card', instanceId: card.dataset.instanceId };
    }
    const stack = element.closest<HTMLElement>('[data-playtest-stack-zone-id]');
    const stackZoneId = stack?.dataset.playtestStackZoneId as PlaytestZoneId | undefined;
    if (stackZoneId) {
      return { type: 'zone', zoneId: stackZoneId };
    }
    const zone = element.closest<HTMLElement>('[data-playtest-drop-zone]');
    const zoneId = zone?.dataset.playtestDropZone as PlaytestZoneId | 'board' | undefined;
    if (zoneId) {
      return { type: 'zone', zoneId };
    }
  }

  return null;
};
