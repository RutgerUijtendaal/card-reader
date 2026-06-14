import type { DeckCardSummary, DeckRecord } from '@/modules/decks/types';

export type PlaytestZoneId = 'library' | 'hand' | 'play' | 'discard' | 'banish' | 'other' | 'hero';

export type PlaytestPhase = 'opening' | 'play';

export type PlaytestStackFace = 'front' | 'back';

export type PlaytestStackDefaultAction = 'draw' | 'open';

export type PlaytestStackDefinition = {
  id: PlaytestZoneId;
  label: string;
  defaultAction: PlaytestStackDefaultAction;
};

export type PlaytestCardSource =
  | { type: 'card'; zoneId: PlaytestZoneId }
  | { type: 'stack'; zoneId: PlaytestZoneId };

export type PlaytestDropTarget =
  | { type: 'zone'; zoneId: PlaytestZoneId | 'board' }
  | { type: 'card'; instanceId: string }
  | { type: 'stack'; zoneId: PlaytestZoneId };

export type PlaytestDraggedCard = {
  instanceId: string;
  groupInstanceIds?: string[];
  groupOffsets?: Record<string, { pointerOffsetX: number; pointerOffsetY: number }>;
  source: PlaytestCardSource;
  pointerId: number;
  pointerOffsetX: number;
  pointerOffsetY: number;
  sourceWidth: number;
  sourceHeight: number;
  pointerX: number;
  pointerY: number;
  ctrlKey: boolean;
  candidate: PlaytestDropTarget | null;
};

export type PlaytestHoverTarget =
  | { type: 'card'; instanceId: string }
  | { type: 'stack'; zoneId: PlaytestZoneId };

export type PlaytestEntityAction = {
  id: string;
  label: string;
  disabled?: boolean;
  run: () => void;
};

export type PlaytestCardInstance = {
  instanceId: string;
  cardId: string;
  card: DeckCardSummary;
  zoneId: PlaytestZoneId;
  order: number;
  tapped: boolean;
  setupOrigin: boolean;
  boardX: number | null;
  boardY: number | null;
  pileGroupId: string | null;
  pileOrder: number | null;
};

export type PlaytestSetupSnapshot = {
  instances: PlaytestCardInstance[];
};

export type PlaytestOpeningSetup = {
  selectedManaInstanceIds: string[];
  selectedSetupInstanceIds: string[];
};

export type PlaytestState = {
  deckId: string;
  deckUpdatedAt: string;
  phase: PlaytestPhase;
  handSize: number;
  instances: PlaytestCardInstance[];
  stackFaces: Partial<Record<PlaytestZoneId, PlaytestStackFace>>;
  openingSetup: PlaytestOpeningSetup;
  setupSnapshot: PlaytestSetupSnapshot | null;
};

export type PublicCardBackRecord = {
  id: string;
  label: string;
  width: number;
  height: number;
  image_url: string | null;
  created_at: string;
  updated_at: string;
};

export type CardBackCurrentResponse = {
  current: PublicCardBackRecord | null;
};

export type StoredPlaytestDraft = {
  version: 3;
  deckId: string;
  deckUpdatedAt: string;
  state: PlaytestState;
  savedAt: string;
};

export type PlaytestStorageAdapter = {
  load: (deckId: string) => StoredPlaytestDraft | null;
  save: (draft: StoredPlaytestDraft) => void;
  clear: (deckId: string) => void;
};

export type PlaytestDeckSuggestion = {
  deck: DeckRecord;
  source: 'owned' | 'public';
};
