import { cardRoleLabel, CARD_ROLE_OPTIONS } from '@/domain/cards/cardRoles';
import type { CardRole } from '@/domain/cards/cardRoles';
import { cardFactionLabel, CARD_FACTION_OPTIONS } from '@/domain/cards/cardFactions';
import type { CardFaction } from '@/domain/cards/cardFactions';
import { cardPoolLabel, isCardPool } from '@/domain/cards/cardPools';
import type { ImportJobItem, ImportWarning } from '@/features/import-jobs/types';
import { isTerminalImportStatus } from '@/features/import-jobs/utils/importJobUtils';

export type ImportEvidenceState =
  | 'pending'
  | 'resolved'
  | 'resolved_with_warning'
  | 'unavailable';

export type ImportEvidenceEntry = { label: string; value: string };

const CARD_ROLE_VALUES: ReadonlySet<string> = new Set(
  CARD_ROLE_OPTIONS.map((option) => option.value),
);
const CARD_FACTION_VALUES: ReadonlySet<string> = new Set(
  CARD_FACTION_OPTIONS.map((option) => option.value),
);

const asRecord = (value: unknown): Record<string, unknown> | null =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;

const asCardRoles = (value: unknown): CardRole[] =>
  Array.isArray(value)
    ? value.filter(
      (item): item is CardRole => typeof item === 'string' && CARD_ROLE_VALUES.has(item),
    )
    : [];

const asCardFactions = (value: unknown): CardFaction[] =>
  Array.isArray(value)
    ? value.filter(
      (item): item is CardFaction => typeof item === 'string' && CARD_FACTION_VALUES.has(item),
    )
    : [];

const asStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

export const formatImportRoles = (value: unknown): string => {
  const roles = asCardRoles(value);
  return roles.length > 0 ? roles.map(cardRoleLabel).join(', ') : 'Normal';
};

export const formatImportFactions = (value: unknown): string => {
  const factions = asCardFactions(value);
  return factions.length > 0 ? factions.map(cardFactionLabel).join(', ') : 'None';
};

const formatPool = (value: unknown): string =>
  isCardPool(value) ? cardPoolLabel(value) : 'Unknown';

const formatClassification = (value: unknown): string | null => {
  const classification = asRecord(value);
  if (!classification) return null;
  return `${formatPool(classification.card_pool)} · ${formatImportRoles(classification.card_roles)} · ${formatImportFactions(classification.card_factions)}`;
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
  const roleMode = roleEvidence.mode === 'override'
    ? 'Manual override'
    : roleEvidence.mode === 'automatic' ? 'Automatic' : 'Unavailable';
  const factionMode = factionEvidence.mode === 'override'
    ? 'Manual override'
    : factionEvidence.mode === 'automatic' ? 'Automatic' : 'Unavailable';
  const entries: ImportEvidenceEntry[] = [
    { label: 'Role resolution', value: roleMode },
    { label: 'Faction resolution', value: factionMode },
  ];
  const templateRoles = asCardRoles(roleEvidence.template_roles);
  const roleMatchedTags = asStringArray(roleEvidence.matched_tag_keys);
  const overrideRoles = asCardRoles(roleEvidence.override_roles);
  const templateFactions = asCardFactions(factionEvidence.template_factions);
  const factionMatchedTags = asStringArray(factionEvidence.matched_tag_keys);
  const overrideFactions = asCardFactions(factionEvidence.override_factions);

  if (roleEvidence.mode && templateRoles.length > 0) {
    entries.push({ label: 'Template hints', value: templateRoles.map(cardRoleLabel).join(', ') });
  }
  if (roleEvidence.mode && roleMatchedTags.length > 0) {
    entries.push({ label: 'Role tags', value: roleMatchedTags.join(', ') });
  }
  if (roleEvidence.mode === 'override') {
    entries.push({ label: 'Override roles', value: formatImportRoles(overrideRoles) });
  }
  if (templateRoles.length === 0 && roleMatchedTags.length === 0 && roleEvidence.mode === 'automatic') {
    entries.push({ label: 'Role signals', value: 'None matched' });
  }
  if (factionEvidence.mode && templateFactions.length > 0) {
    entries.push({ label: 'Template faction hints', value: formatImportFactions(templateFactions) });
  }
  if (factionEvidence.mode && factionMatchedTags.length > 0) {
    entries.push({ label: 'Faction tags', value: factionMatchedTags.join(', ') });
  }
  if (factionEvidence.mode === 'override') {
    entries.push({ label: 'Override factions', value: formatImportFactions(overrideFactions) });
  }
  if (
    templateFactions.length === 0
    && factionMatchedTags.length === 0
    && factionEvidence.mode === 'automatic'
  ) {
    entries.push({ label: 'Faction signals', value: 'None matched' });
  }
  return entries;
};

export const getWarningEvidence = (warning: ImportWarning): ImportEvidenceEntry[] => {
  const details = warning.details;
  if (!details) return [];
  const entries: ImportEvidenceEntry[] = [];
  const labels: Array<[string, string]> = [
    ['inferred', 'Inferred'],
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
