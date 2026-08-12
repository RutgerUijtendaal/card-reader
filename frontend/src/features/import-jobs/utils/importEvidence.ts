import { cardRoleLabel, CARD_ROLE_OPTIONS } from '@/domain/cards/cardRoles';
import type { CardRole } from '@/domain/cards/cardRoles';
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

const asStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

export const formatImportRoles = (value: unknown): string => {
  const roles = asCardRoles(value);
  return roles.length > 0 ? roles.map(cardRoleLabel).join(', ') : 'Standard';
};

const formatPool = (value: unknown): string =>
  isCardPool(value) ? cardPoolLabel(value) : 'Unknown';

const formatClassification = (value: unknown): string | null => {
  const classification = asRecord(value);
  if (!classification) return null;
  return `${formatPool(classification.card_pool)} · ${formatImportRoles(classification.card_roles)}`;
};

export const getImportEvidenceState = (item: ImportJobItem): ImportEvidenceState => {
  const hasEvidence = Object.keys(item.card_role_inference).length > 0;
  if (hasEvidence && item.warnings.length > 0) return 'resolved_with_warning';
  if (hasEvidence) return 'resolved';
  return isTerminalImportStatus(item.status) ? 'unavailable' : 'pending';
};

export const getImportEvidencePlaceholder = (state: ImportEvidenceState): string =>
  state === 'pending' ? 'Classification pending' : 'Classification unavailable';

export const getInferenceEvidence = (item: ImportJobItem): ImportEvidenceEntry[] => {
  const evidence = item.card_role_inference;
  const mode = evidence.mode === 'override' ? 'Manual override' : 'Automatic';
  const entries: ImportEvidenceEntry[] = [{ label: 'Resolution', value: mode }];
  const templateRoles = asCardRoles(evidence.template_roles);
  const matchedTags = asStringArray(evidence.matched_tag_keys);
  const overrideRoles = asCardRoles(evidence.override_roles);

  if (templateRoles.length > 0) {
    entries.push({ label: 'Template hints', value: templateRoles.map(cardRoleLabel).join(', ') });
  }
  if (matchedTags.length > 0) {
    entries.push({ label: 'Matched tags', value: matchedTags.join(', ') });
  }
  if (evidence.mode === 'override') {
    entries.push({ label: 'Override roles', value: formatImportRoles(overrideRoles) });
  }
  if (templateRoles.length === 0 && matchedTags.length === 0 && evidence.mode !== 'override') {
    entries.push({ label: 'Role signals', value: 'None matched' });
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
