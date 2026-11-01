import type { DeckDifficulty, DeckVisibility } from '@/domain/decks/types';

export type DeckFormEntry = {
  card_id: string;
  quantity: number;
};

export type DeckFormSideboard = {
  id: string;
  source_id?: string;
  name: string;
  entries: DeckFormEntry[];
};

export type DeckForm = {
  name: string;
  description: string;
  long_description: string;
  difficulty: DeckDifficulty | null;
  visibility: DeckVisibility;
  hero_card_id: string;
  entries: DeckFormEntry[];
  sideboards: DeckFormSideboard[];
  tag_ids: string[];
  suggested_type_labels: string[];
};

/** Which part of the card pool the builder shows; deck details open as a separate overlay. */
export type DeckEditorMode = 'hero' | 'cards';

export type DeckBoardMoveDestination = {
  boardId: string;
  label: string;
  description?: string;
  disabled: boolean;
};

export type DeckBoardEntryChangeKind = 'add' | 'remove';

export type DeckBoardEntryChange = {
  cardId: string;
  boardId: string;
  kind: DeckBoardEntryChangeKind;
  sequence: number;
};
