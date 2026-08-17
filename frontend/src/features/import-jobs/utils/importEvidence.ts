import { displayCardRoleLabels, isCardRole } from '@/domain/cards/cardRoles';
import type { CardRole } from '@/domain/cards/cardRoles';
import { displayCardFactionLabels, isCardFaction } from '@/domain/cards/cardFactions';
import type { CardFaction } from '@/domain/cards/cardFactions';
import { cardPoolLabel, isCardPool } from '@/domain/cards/cardPools';
import {
  displayManaFamilyLabels,
  isManaFamily,
  type ManaFamily,
} from '@/domain/cards/manaFamilies';
import type { ImportJobItem, ImportWarning } from '@/features/import-jobs/types';
import { isTerminalImportStatus } from '@/features/import-jobs/utils/importJobUtils';

export type ImportEvidenceState =
  | 'pending'
  | 'resolved'
  | 'resolved_with_warning'
  | 'unavailable';

export type ImportEvidenceEntry = { label: string; value: string };

const asRecord = (value: unknown): Record<string, unknown> | null =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;

const asCardRoles = (value: unknown): CardRole[] =>
  Array.isArray(value)
    ? value.filter(
      (item): item is CardRole => typeof item === 'string' && isCardRole(item),
    )
    : [];

const asCardFactions = (value: unknown): CardFaction[] =>
  Array.isArray(value)
    ? value.filter(
      (item): item is CardFaction => typeof item === 'string' && isCardFaction(item),
    )
    : [];

const asManaFamilies = (value: unknown): ManaFamily[] =>
  Array.isArray(value)
    ? value.filter(
      (item): item is ManaFamily => typeof item === 'string' && isManaFamily(item),
    )
    : [];

const sourceLabels = (value: unknown): string[] =>
  Array.isArray(value)
    ? value.flatMap((item) => {
      const source = asRecord(item);
      return typeof source?.key === 'string' ? [source.key] : [];
    })
    : [];

export const formatImportRoles = (value: unknown): string => {
  return displayCardRoleLabels(asCardRoles(value)).join(', ');
};

export const formatImportFactions = (value: unknown): string => {
  return displayCardFactionLabels(asCardFactions(value)).join(', ');
};

export const formatImportManaFamilies = (value: unknown): string => {
  if (!Array.isArray(value)) return 'Unavailable';
  return displayManaFamilyLabels(asManaFamilies(value)).join(', ');
};

export const formatResolvedImportManaFamilies = (item: ImportJobItem): string =>
  asRecord(item.classification_inference.mana_families)
    ? formatImportManaFamilies(item.resolved_card_mana_families)
    : 'Unavailable';

const formatPool = (value: unknown): string =>
  isCardPool(value) ? cardPoolLabel(value) : 'Unknown';

const formatClassification = (value: unknown): string | null => {
  const classification = asRecord(value);
  if (!classification) return null;
  return `${formatPool(classification.card_pool)} · ${formatImportRoles(classification.card_roles)} · ${formatImportFactions(classification.card_factions)} · ${formatImportManaFamilies(classification.card_mana_families)}`;
};

export const getImportEvidenceState = (item: ImportJobItem): ImportEvidenceState => {
  const hasEvidence = Object.keys(item.classification_inference).length > 0;
  if (hasEvidence && item.warnings.length > 0) return 'resolved_with_warning';
  if (hasEvidence) return 'resolved';
  return isTerminalImportStatus(item.status) ? 'unavailable' : 'pending';
};

export const getImportEvidencePlaceholder = (state: ImportEvidenceState): string =>
  state === 'pending' ? 'Classification pending' : 'Classification unavailable';

export const getInferenceEvidence = (item: ImportJobItem): ImportEvidenceEntry[] => {
  const evidence = item.classification_inference;
  const roleEvidence = asRecord(evidence.roles) ?? {};
  const factionEvidence = asRecord(evidence.factions) ?? {};
  const manaEvidence = asRecord(evidence.mana_families) ?? {};
  const roleMode = roleEvidence.mode === 'override'
    ? 'Manual override'
    : roleEvidence.mode === 'automatic' ? 'Automatic' : 'Unavailable';
  const factionMode = factionEvidence.mode === 'override'
    ? 'Manual override'
    : factionEvidence.mode === 'automatic' ? 'Automatic' : 'Unavailable';
  const manaMode = manaEvidence.mode === 'override'
    ? 'Manual override'
    : manaEvidence.mode === 'automatic' ? 'Automatic' : 'Unavailable';
  const entries: ImportEvidenceEntry[] = [
    { label: 'Role resolution', value: roleMode },
    { label: 'Faction resolution', value: factionMode },
    { label: 'Mana resolution', value: manaMode },
  ];
  const roleMatchedTags = sourceLabels(roleEvidence.matched_tag_sources);
  const roleMatchedTypes = sourceLabels(roleEvidence.matched_type_sources);
  const roleMatchedSymbols = sourceLabels(roleEvidence.matched_symbol_sources);
  const overrideRoles = asCardRoles(roleEvidence.override_roles);
  const factionMatchedTags = sourceLabels(factionEvidence.matched_tag_sources);
  const factionMatchedTypes = sourceLabels(factionEvidence.matched_type_sources);
  const factionMatchedSymbols = sourceLabels(factionEvidence.matched_symbol_sources);
  const overrideFactions = asCardFactions(factionEvidence.override_factions);
  const manaMatchedTags = sourceLabels(manaEvidence.matched_tag_sources);
  const manaMatchedTypes = sourceLabels(manaEvidence.matched_type_sources);
  const manaMatchedSymbols = sourceLabels(manaEvidence.matched_symbol_sources);
  const overrideManaFamilies = asManaFamilies(manaEvidence.override_mana_families);

  if (roleEvidence.mode && roleMatchedTags.length > 0) {
    entries.push({ label: 'Role tags', value: roleMatchedTags.join(', ') });
  }
  if (roleEvidence.mode && roleMatchedTypes.length > 0) {
    entries.push({ label: 'Role types', value: roleMatchedTypes.join(', ') });
  }
  if (roleEvidence.mode && roleMatchedSymbols.length > 0) {
    entries.push({ label: 'Role symbols', value: roleMatchedSymbols.join(', ') });
  }
  if (roleEvidence.mode === 'override') {
    entries.push({ label: 'Override roles', value: formatImportRoles(overrideRoles) });
  }
  if (
    roleMatchedTags.length === 0
    && roleMatchedTypes.length === 0
    && roleMatchedSymbols.length === 0
    && roleEvidence.mode === 'automatic'
  ) {
    entries.push({ label: 'Role signals', value: 'None matched' });
  }
  if (factionEvidence.mode && factionMatchedTags.length > 0) {
    entries.push({ label: 'Faction tags', value: factionMatchedTags.join(', ') });
  }
  if (factionEvidence.mode && factionMatchedTypes.length > 0) {
    entries.push({ label: 'Faction types', value: factionMatchedTypes.join(', ') });
  }
  if (factionEvidence.mode && factionMatchedSymbols.length > 0) {
    entries.push({ label: 'Faction symbols', value: factionMatchedSymbols.join(', ') });
  }
  if (factionEvidence.mode === 'override') {
    entries.push({ label: 'Override factions', value: formatImportFactions(overrideFactions) });
  }
  if (
    factionMatchedTags.length === 0
    && factionMatchedTypes.length === 0
    && factionMatchedSymbols.length === 0
    && factionEvidence.mode === 'automatic'
  ) {
    entries.push({ label: 'Faction signals', value: 'None matched' });
  }
  for (const [label, values] of [
    ['Mana tags', manaMatchedTags],
    ['Mana types', manaMatchedTypes],
    ['Mana symbols', manaMatchedSymbols],
  ] as const) {
    if (values.length > 0) entries.push({ label, value: values.join(', ') });
  }
  if (manaEvidence.mode === 'override') {
    entries.push({
      label: 'Override Mana Families',
      value: formatImportManaFamilies(overrideManaFamilies),
    });
  }
  if (
    manaEvidence.mode === 'automatic'
    && manaMatchedTags.length === 0
    && manaMatchedTypes.length === 0
    && manaMatchedSymbols.length === 0
  ) {
    entries.push({ label: 'Mana signals', value: 'None matched' });
  }
  return entries;
};

export const getWarningEvidence = (warning: ImportWarning): ImportEvidenceEntry[] => {
  const details = warning.details;
  if (!details) return [];
  const entries: ImportEvidenceEntry[] = [];
  if (warning.code === 'evil_faction_unresolved') {
    const reasonLabels: Record<string, string> = {
      existing_unresolved_card: 'Existing unresolved Card',
      no_candidate: 'No existing candidate',
      ambiguous_checksum: 'Ambiguous image history',
      ambiguous_name: 'Ambiguous name or alias',
      conflicting_evidence: 'Image and name disagree',
    };
    const reason = details.reason;
    if (typeof reason === 'string' && reasonLabels[reason]) {
      entries.push({ label: 'Match result', value: reasonLabels[reason] });
    }
    const checksumCount = details.checksum_candidate_count;
    if (typeof checksumCount === 'number' && Number.isInteger(checksumCount)) {
      entries.push({ label: 'Image candidates', value: String(checksumCount) });
    }
    const nameCount = details.name_candidate_count;
    if (typeof nameCount === 'number' && Number.isInteger(nameCount)) {
      entries.push({ label: 'Name candidates', value: String(nameCount) });
    }
    return entries;
  }
  const labels: Array<[string, string]> = [
    ['inferred', 'Inferred'],
    ['stored', 'Stored'],
    ['existing', 'Existing'],
    ['queued', 'Queued'],
    ['live', 'Live'],
  ];
  for (const [key, label] of labels) {
    const value = formatClassification(details[key]);
    if (value) entries.push({ label, value });
  }
  return entries;
};
