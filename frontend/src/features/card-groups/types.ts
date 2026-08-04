import type { CardDeckReferenceSummary } from '@/domain/card-deck-references/types';
import type { CardVersionDetail } from '@/domain/cards/types';

export type CardGroupMemberDetail = {
  position: number;
  is_anchor: boolean;
  card: CardVersionDetail;
};

export type CardGroupDetail = {
  id: string;
  key: string;
  name: string;
  anchor_card_id: string;
  anchor_deck_references: CardDeckReferenceSummary[];
  member_count: number;
  members: CardGroupMemberDetail[];
};
