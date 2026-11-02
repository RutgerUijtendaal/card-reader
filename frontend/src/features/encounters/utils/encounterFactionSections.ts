import { CARD_FACTION_OPTIONS, cardFactionLabel, isCardFaction } from '@/domain/cards/cardFactions';
import type { EncounterSummary } from '@/domain/encounters/types';

export type EncounterFactionSection = {
  key: string;
  label: string;
  encounters: EncounterSummary[];
};

const MIXED_SECTION = { key: 'mixed', label: 'Multiple factions' };
const NONE_SECTION = { key: 'none', label: 'No faction' };

const sectionFor = (encounter: EncounterSummary): { key: string; label: string } => {
  if (encounter.factions.length > 1) {
    return MIXED_SECTION;
  }
  const [faction] = encounter.factions;
  if (faction && isCardFaction(faction)) {
    return { key: faction, label: cardFactionLabel(faction) };
  }
  return NONE_SECTION;
};

const SECTION_ORDER = [
  ...CARD_FACTION_OPTIONS.map((option) => option.value as string),
  MIXED_SECTION.key,
  NONE_SECTION.key,
];

/**
 * Splits loaded Encounters into faction sections: one per single faction in canonical order, then
 * Encounters with several factions, then those with none. The API pages in this same order, so
 * loading more only extends the last section or adds new ones after it.
 */
export const groupEncountersByFaction = (
  encounters: readonly EncounterSummary[],
): EncounterFactionSection[] => {
  const sections = new Map<string, EncounterFactionSection>();
  for (const encounter of encounters) {
    const { key, label } = sectionFor(encounter);
    let section = sections.get(key);
    if (!section) {
      section = { key, label, encounters: [] };
      sections.set(key, section);
    }
    section.encounters.push(encounter);
  }
  return [...sections.values()].sort(
    (left, right) => SECTION_ORDER.indexOf(left.key) - SECTION_ORDER.indexOf(right.key),
  );
};
