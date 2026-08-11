import {
  normalizeCardFilterSelectionState,
  type CardFilterSelectionState,
} from '@/domain/cards/utils/filters/cardFilterState';
import { LEGACY_MANA_SYMBOL_ID_PREFIX } from '@/domain/cards/utils/filters/cardFilterSelection';
import {
  buildCardLifecycleApiParams,
  type CardLifecycleFilterValue,
} from '@/domain/cards/utils/filters/cardLifecycle';
import type { CardRoleFilter } from '@/domain/cards/cardRoles';
import type { CardPool } from '@/domain/cards/types/cardModels';

export type CardFilterApiPayload = {
  q?: string;
  lifecycle_status?: CardLifecycleFilterValue;
  card_pool?: CardPool;
  card_roles?: CardRoleFilter[];
  card_role_exclude?: CardRoleFilter[];
  card_role_match?: 'any' | 'all';
  keyword_ids?: string[];
  keyword_match?: 'any' | 'all';
  tag_ids?: string[];
  tag_match?: 'any' | 'all';
  type_ids?: string[];
  type_exclude_ids?: string[];
  type_match?: 'any' | 'all';
  mana_family_keys?: string[];
  mana_family_exclude_keys?: string[];
  mana_family_match?: 'any' | 'all';
  mana_symbol_ids?: string[];
  mana_symbol_exclude_ids?: string[];
  mana_symbol_match?: 'any' | 'all';
  affinity_symbol_ids?: string[];
  affinity_symbol_exclude_ids?: string[];
  affinity_symbol_match?: 'any' | 'all';
  devotion_symbol_ids?: string[];
  devotion_symbol_exclude_ids?: string[];
  devotion_symbol_match?: 'any' | 'all';
  other_symbol_ids?: string[];
  other_symbol_exclude_ids?: string[];
  other_symbol_match?: 'any' | 'all';
  template_id?: string;
  mana_cost_min?: string;
  mana_cost_max?: string;
  attack_min?: string;
  attack_max?: string;
  health_min?: string;
  health_max?: string;
};

export const buildCardFilterApiPayload = (
  state: CardFilterSelectionState,
): CardFilterApiPayload => {
  const normalized = normalizeCardFilterSelectionState(state);
  const legacyManaSymbolIds = normalized.manaTypeSymbolIds
    .filter((id) => id.startsWith(LEGACY_MANA_SYMBOL_ID_PREFIX))
    .map((id) => id.slice(LEGACY_MANA_SYMBOL_ID_PREFIX.length));
  const manaFamilyKeys = normalized.manaTypeSymbolIds.filter(
    (id) => !id.startsWith(LEGACY_MANA_SYMBOL_ID_PREFIX),
  );
  const legacyManaSymbolExcludeIds = normalized.manaTypeSymbolExcludeIds
    .filter((id) => id.startsWith(LEGACY_MANA_SYMBOL_ID_PREFIX))
    .map((id) => id.slice(LEGACY_MANA_SYMBOL_ID_PREFIX.length));
  const manaFamilyExcludeKeys = normalized.manaTypeSymbolExcludeIds.filter(
    (id) => !id.startsWith(LEGACY_MANA_SYMBOL_ID_PREFIX),
  );
  const payload: CardFilterApiPayload = { card_pool: normalized.cardPool };

  if (normalized.query) payload.q = normalized.query;
  Object.assign(payload, buildCardLifecycleApiParams(normalized.lifecycleStatus));
  if (normalized.cardRoleIds.length > 0) {
    payload.card_roles = normalized.cardRoleIds;
    payload.card_role_match = normalized.cardRoleMatch;
  }
  if (normalized.cardRoleExcludeIds.length > 0) {
    payload.card_role_exclude = normalized.cardRoleExcludeIds;
  }
  if (normalized.keywordIds.length > 0) {
    payload.keyword_ids = normalized.keywordIds;
    payload.keyword_match = normalized.keywordMatch;
  }
  if (normalized.tagIds.length > 0) {
    payload.tag_ids = normalized.tagIds;
    payload.tag_match = normalized.tagMatch;
  }
  if (normalized.typeIds.length > 0) {
    payload.type_ids = normalized.typeIds;
    payload.type_match = normalized.typeMatch;
  }
  if (normalized.typeExcludeIds.length > 0) payload.type_exclude_ids = normalized.typeExcludeIds;
  if (manaFamilyKeys.length > 0) {
    payload.mana_family_keys = manaFamilyKeys;
    payload.mana_family_match = normalized.manaSymbolMatch;
  }
  if (manaFamilyExcludeKeys.length > 0)
    payload.mana_family_exclude_keys = manaFamilyExcludeKeys;
  if (legacyManaSymbolIds.length > 0) {
    payload.mana_symbol_ids = legacyManaSymbolIds;
    payload.mana_symbol_match = normalized.manaSymbolMatch;
  }
  if (legacyManaSymbolExcludeIds.length > 0)
    payload.mana_symbol_exclude_ids = legacyManaSymbolExcludeIds;
  if (normalized.affinitySymbolIds.length > 0) {
    payload.affinity_symbol_ids = normalized.affinitySymbolIds;
    payload.affinity_symbol_match = normalized.affinitySymbolMatch;
  }
  if (normalized.affinitySymbolExcludeIds.length > 0)
    payload.affinity_symbol_exclude_ids = normalized.affinitySymbolExcludeIds;
  if (normalized.devotionSymbolIds.length > 0) {
    payload.devotion_symbol_ids = normalized.devotionSymbolIds;
    payload.devotion_symbol_match = normalized.devotionSymbolMatch;
  }
  if (normalized.devotionSymbolExcludeIds.length > 0)
    payload.devotion_symbol_exclude_ids = normalized.devotionSymbolExcludeIds;
  if (normalized.otherSymbolIds.length > 0) {
    payload.other_symbol_ids = normalized.otherSymbolIds;
    payload.other_symbol_match = normalized.otherSymbolMatch;
  }
  if (normalized.otherSymbolExcludeIds.length > 0)
    payload.other_symbol_exclude_ids = normalized.otherSymbolExcludeIds;
  if (normalized.templateId) payload.template_id = normalized.templateId;
  if (normalized.manaCostMin) payload.mana_cost_min = normalized.manaCostMin;
  if (normalized.manaCostMax) payload.mana_cost_max = normalized.manaCostMax;
  if (normalized.attackMin) payload.attack_min = normalized.attackMin;
  if (normalized.attackMax) payload.attack_max = normalized.attackMax;
  if (normalized.healthMin) payload.health_min = normalized.healthMin;
  if (normalized.healthMax) payload.health_max = normalized.healthMax;

  return payload;
};

export const buildCardFilterApiSearchParams = (
  state: CardFilterSelectionState,
): URLSearchParams => {
  const payload = buildCardFilterApiPayload(state);
  const normalized = normalizeCardFilterSelectionState(state);
  const params = new URLSearchParams();
  params.set('card_pool', payload.card_pool ?? 'player');

  if (payload.q) params.set('q', payload.q);
  if (payload.lifecycle_status) params.set('lifecycle_status', payload.lifecycle_status);
  payload.card_roles?.forEach((role) => params.append('card_roles', role));
  payload.card_role_exclude?.forEach((role) => params.append('card_role_exclude', role));
  if (payload.card_roles) params.set('card_role_match', payload.card_role_match ?? normalized.cardRoleMatch);
  if (payload.keyword_ids) {
    payload.keyword_ids.forEach((id) => params.append('keyword_ids', id));
    params.set('keyword_match', payload.keyword_match ?? normalized.keywordMatch);
  }
  if (payload.tag_ids) {
    payload.tag_ids.forEach((id) => params.append('tag_ids', id));
    params.set('tag_match', payload.tag_match ?? normalized.tagMatch);
  }
  if (payload.type_ids) {
    payload.type_ids.forEach((id) => params.append('type_ids', id));
    params.set('type_match', payload.type_match ?? normalized.typeMatch);
  }
  payload.type_exclude_ids?.forEach((id) => params.append('type_exclude_ids', id));
  if (payload.mana_family_keys) {
    payload.mana_family_keys.forEach((key) => params.append('mana_family_keys', key));
    params.set('mana_family_match', payload.mana_family_match ?? normalized.manaSymbolMatch);
  }
  payload.mana_family_exclude_keys?.forEach((key) => params.append('mana_family_exclude_keys', key));
  if (payload.mana_symbol_ids) {
    payload.mana_symbol_ids.forEach((id) => params.append('mana_symbol_ids', id));
    params.set('mana_symbol_match', payload.mana_symbol_match ?? normalized.manaSymbolMatch);
  }
  payload.mana_symbol_exclude_ids?.forEach((id) => params.append('mana_symbol_exclude_ids', id));
  if (payload.affinity_symbol_ids) {
    payload.affinity_symbol_ids.forEach((id) => params.append('affinity_symbol_ids', id));
    params.set('affinity_symbol_match', payload.affinity_symbol_match ?? normalized.affinitySymbolMatch);
  }
  payload.affinity_symbol_exclude_ids?.forEach((id) => params.append('affinity_symbol_exclude_ids', id));
  if (payload.devotion_symbol_ids) {
    payload.devotion_symbol_ids.forEach((id) => params.append('devotion_symbol_ids', id));
    params.set('devotion_symbol_match', payload.devotion_symbol_match ?? normalized.devotionSymbolMatch);
  }
  payload.devotion_symbol_exclude_ids?.forEach((id) => params.append('devotion_symbol_exclude_ids', id));
  if (payload.other_symbol_ids) {
    payload.other_symbol_ids.forEach((id) => params.append('other_symbol_ids', id));
    params.set('other_symbol_match', payload.other_symbol_match ?? normalized.otherSymbolMatch);
  }
  payload.other_symbol_exclude_ids?.forEach((id) => params.append('other_symbol_exclude_ids', id));
  if (payload.template_id) params.set('template_id', payload.template_id);
  if (payload.mana_cost_min) params.set('mana_cost_min', payload.mana_cost_min);
  if (payload.mana_cost_max) params.set('mana_cost_max', payload.mana_cost_max);
  if (payload.attack_min) params.set('attack_min', payload.attack_min);
  if (payload.attack_max) params.set('attack_max', payload.attack_max);
  if (payload.health_min) params.set('health_min', payload.health_min);
  if (payload.health_max) params.set('health_max', payload.health_max);

  return params;
};
