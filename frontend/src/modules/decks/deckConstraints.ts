import {
  MAX_DECK_COPIES,
  MAX_SIDEBOARD_ENTRY_QUANTITY,
} from '@/modules/decks/constants';
import type { DeckMetadataOption } from '@/modules/decks/types';

export const LEGENDARY_COPY_LIMIT_MESSAGE = 'Legendary cards are limited to 1 copy per deck.';

export type DeckConstraintCard = {
  id: string;
  types: DeckMetadataOption[];
};

export type DeckConstraintEntry = {
  card_id: string;
  quantity: number;
};

export type DeckConstraintSideboard = {
  id: string;
  entries: DeckConstraintEntry[];
};

export type DeckConstraintContext = {
  mainboardId: string;
  boardId: string;
  mainboardEntries: DeckConstraintEntry[];
  sideboards: DeckConstraintSideboard[];
};

export type DeckQuantityLimit = {
  max: number;
  message: string;
};

export const isLegendaryCard = (card: DeckConstraintCard | null | undefined): boolean =>
  Boolean(card?.types.some((type) => type.key.trim().toLowerCase() === 'legendary'));

export const getDeckEntryQuantityLimit = (
  card: DeckConstraintCard,
  context: DeckConstraintContext,
): DeckQuantityLimit => {
  const boardMax = context.boardId === context.mainboardId ? MAX_DECK_COPIES : MAX_SIDEBOARD_ENTRY_QUANTITY;
  if (!isLegendaryCard(card)) {
    return {
      max: boardMax,
      message:
        context.boardId === context.mainboardId
          ? `Mainboard copy limit is ${MAX_DECK_COPIES}.`
          : `Sideboard copy limit is ${MAX_SIDEBOARD_ENTRY_QUANTITY}.`,
    };
  }

  const otherCopies = getCopiesOutsideBoard(card.id, context);
  return {
    max: Math.min(boardMax, Math.max(0, 1 - otherCopies)),
    message: LEGENDARY_COPY_LIMIT_MESSAGE,
  };
};

export const getDeckQuantityViolationMessage = (
  card: DeckConstraintCard,
  quantity: number,
  context: DeckConstraintContext,
): string | null => {
  const limit = getDeckEntryQuantityLimit(card, context);
  return quantity > limit.max ? limit.message : null;
};

export const getDeckConstraintMessages = (
  cardLookup: Record<string, DeckConstraintCard>,
  context: Omit<DeckConstraintContext, 'boardId'>,
): string[] => {
  const messages = new Set<string>();
  const validateEntries = (boardId: string, entries: DeckConstraintEntry[]): void => {
    for (const entry of entries) {
      const card = cardLookup[entry.card_id];
      if (!card) {
        continue;
      }
      const message = getDeckQuantityViolationMessage(card, entry.quantity, {
        ...context,
        boardId,
      });
      if (message) {
        messages.add(message);
      }
    }
  };

  validateEntries(context.mainboardId, context.mainboardEntries);
  for (const sideboard of context.sideboards) {
    validateEntries(sideboard.id, sideboard.entries);
  }

  return [...messages];
};

const getCopiesOutsideBoard = (cardId: string, context: DeckConstraintContext): number => {
  let count = 0;
  if (context.boardId !== context.mainboardId) {
    count += getEntryQuantity(context.mainboardEntries, cardId);
  }
  for (const sideboard of context.sideboards) {
    if (sideboard.id !== context.boardId) {
      count += getEntryQuantity(sideboard.entries, cardId);
    }
  }
  return count;
};

const getEntryQuantity = (entries: DeckConstraintEntry[], cardId: string): number =>
  entries.find((entry) => entry.card_id === cardId)?.quantity ?? 0;
