import type { FormSideboard } from '@/domain/cards/composables/useCardCollectionBoards';
import type { CardFaction } from '@/domain/cards/cardFactions';
import type { CardListItem } from '@/domain/cards/types';

export type EncounterDraft = {
  name: string;
  description_markup: string;
  long_description_markup: string;
  boss_card_id: string | null;
  boss_group_id: string | null;
  factions: CardFaction[];
  visibility: 'private' | 'public';
  entries: Array<{ card_id: string; quantity: number }>;
  sideboards: FormSideboard[];
};

export type EncounterSummary = {
  id: string;
  name: string;
  description: string;
  factions: CardFaction[];
  visibility: 'private' | 'public';
  revision: number;
  creator: { id: string; username: string };
  boss_card_id: string | null;
  boss_group_id: string | null;
  boss_card: CardListItem | null;
  total_cards: number;
  sideboard_count: number;
  status: { is_valid: boolean; issues: string[] };
  created_at: string;
  updated_at: string;
};
export type EncounterRecord = EncounterSummary &
  Omit<EncounterDraft, 'entries' | 'sideboards'> & {
    long_description: string;
    boss_cards: CardListItem[];
    sideboards: Array<{
      id: string;
      name: string;
      entries: Array<{ card_id: string; quantity: number; card: CardListItem }>;
    }>;
    entries: Array<{ card_id: string; quantity: number; card: CardListItem }>;
  };
export type EncounterPage = {
  count: number;
  next_page: number | null;
  results: EncounterSummary[];
};
export const emptyEncounter = (): EncounterDraft => ({
  name: '',
  description_markup: '',
  long_description_markup: '',
  boss_card_id: null,
  boss_group_id: null,
  factions: [],
  visibility: 'private',
  entries: [],
  sideboards: [],
});
export const encounterDraftFromRecord = (record: EncounterRecord): EncounterDraft => ({
  name: record.name,
  description_markup: record.description_markup,
  long_description_markup: record.long_description_markup,
  boss_card_id: record.boss_card_id,
  boss_group_id: record.boss_group_id,
  factions: [...record.factions],
  visibility: record.visibility,
  sideboards: record.sideboards.map((board) => ({
    id: board.id,
    source_id: board.id,
    name: board.name,
    entries: board.entries.map(({ card_id, quantity }) => ({ card_id, quantity })),
  })),
  entries: record.entries.map(({ card_id, quantity }) => ({ card_id, quantity })),
});
