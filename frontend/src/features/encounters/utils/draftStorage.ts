import {
  createDraftStorage,
  type DraftSlot,
  type StoredDraft,
  type Attempt,
  type RetiredDraft,
} from '@/shared/drafts/storage';
import type { EncounterDraft } from '@/domain/encounters/types';
import type { CardListItem } from '@/domain/cards/types';
import { isCardFaction } from '@/domain/cards/cardFactions';

export type EncounterStoredDraft = StoredDraft<EncounterDraft, CardListItem, EncounterDraft>;
export type EncounterSlot = DraftSlot<EncounterDraft, CardListItem, EncounterDraft>;
export const encounterDraftKey = (owner: string): string =>
  `card-reader.encounter-editor.new-draft.${owner}`;
const isObject = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === 'object';
const isEntry = (entry: unknown): boolean =>
  isObject(entry) &&
  typeof entry.card_id === 'string' &&
  Number.isInteger(entry.quantity) &&
  Number(entry.quantity) > 0;
export const isEncounterDraft = (value: unknown): value is EncounterDraft => {
  if (!isObject(value)) return false;
  return (
    (value.is_official === undefined || typeof value.is_official === 'boolean') &&
    typeof value.name === 'string' &&
    typeof value.description_markup === 'string' &&
    typeof value.long_description_markup === 'string' &&
    (value.boss_card_id === null || typeof value.boss_card_id === 'string') &&
    (value.boss_group_id === null || typeof value.boss_group_id === 'string') &&
    ['private', 'unlisted', 'public'].includes(String(value.visibility)) &&
    Array.isArray(value.factions) &&
    value.factions.every(isCardFaction) &&
    (value.sideboards === undefined ||
      (Array.isArray(value.sideboards) &&
        value.sideboards.every(
          (board: unknown) =>
            isObject(board) &&
            typeof board.id === 'string' &&
            typeof board.name === 'string' &&
            (board.source_id === undefined || typeof board.source_id === 'string') &&
            Array.isArray(board.entries) &&
            board.entries.every(isEntry),
        ))) &&
    Array.isArray(value.entries) &&
    value.entries.every(isEntry)
  );
};
export const parseEncounterDraft = (value: unknown, owner: string): EncounterSlot | null => {
  if (
    !isObject(value) ||
    value.version !== 2 ||
    value.ownerId !== owner ||
    typeof value.draftId !== 'string' ||
    typeof value.revision !== 'string'
  )
    return null;
  if (
    value.kind === 'retired' &&
    typeof value.createdDeckId === 'string' &&
    typeof value.retiredAt === 'string'
  ) {
    return { kind: 'retired', marker: value as RetiredDraft };
  }
  if (
    value.kind !== 'draft' ||
    typeof value.savedAt !== 'string' ||
    !isEncounterDraft(value.form) ||
    !isObject(value.cards)
  )
    return null;
  if (
    !Object.values(value.cards).every(
      (card) => isObject(card) && typeof card.id === 'string' && card.result_type === 'card',
    )
  )
    return null;
  const attempt = value.pendingCreateAttempt;
  if (
    attempt !== null &&
    (!isObject(attempt) ||
      !isEncounterDraft(attempt.payload) ||
      typeof attempt.signature !== 'string' ||
      typeof attempt.startedAt !== 'string')
  )
    return null;
  return { kind: 'draft', draft: value as EncounterStoredDraft };
};
export const buildEncounterDraft = (
  ownerId: string,
  draftId: string,
  form: EncounterDraft,
  cards: Record<string, CardListItem>,
  pendingCreateAttempt: Attempt<EncounterDraft> | null,
): EncounterStoredDraft => {
  const ids = new Set([
    form.boss_card_id,
    ...form.entries.map((entry) => entry.card_id),
    ...form.sideboards.flatMap((board) => board.entries.map((entry) => entry.card_id)),
  ]);
  return JSON.parse(
    JSON.stringify({
      version: 2,
      kind: 'draft',
      ownerId,
      draftId,
      revision: crypto.randomUUID(),
      savedAt: new Date().toISOString(),
      form,
      cards: Object.fromEntries(Object.entries(cards).filter(([id]) => ids.has(id))),
      pendingCreateAttempt,
    }),
  ) as EncounterStoredDraft;
};
export const createEncounterDraftStorage = () =>
  createDraftStorage({ key: encounterDraftKey, parse: parseEncounterDraft });
