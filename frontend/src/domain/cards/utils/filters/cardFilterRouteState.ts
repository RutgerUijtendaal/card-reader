import type { LocationQuery, LocationQueryRaw, LocationQueryValue } from 'vue-router';
import {
  normalizeCardFilterState,
  type CardFilterState,
} from '@/domain/cards/utils/filters/cardFilterState';
import {
  DEFAULT_CARD_LIFECYCLE_FILTER,
  normalizeCardLifecycleFilterValue,
} from '@/domain/cards/utils/filters/cardLifecycle';
import { isCardRoleFilter, type CardRoleFilter } from '@/domain/cards/cardRoles';
import { normalizeCardPool } from '@/domain/cards/cardPools';
import { isCardFaction, type CardFaction } from '@/domain/cards/cardFactions';

const readQueryValues = (
  value:
    | LocationQueryValue
    | LocationQueryValue[]
    | readonly LocationQueryValue[]
    | null
    | undefined,
): string[] => {
  if (Array.isArray(value)) {
    return value.filter((entry): entry is string => typeof entry === 'string');
  }
  return typeof value === 'string' ? [value] : [];
};

const readCardRoleValues = (value: LocationQueryValue | LocationQueryValue[] | undefined): CardRoleFilter[] =>
  readQueryValues(value).filter(isCardRoleFilter);
const readCardFactionValues = (
  value: LocationQueryValue | LocationQueryValue[] | undefined,
): CardFaction[] => readQueryValues(value).filter(isCardFaction);

export const parseCardFilterRouteQuery = (query: LocationQuery): CardFilterState =>
  normalizeCardFilterState({
    query: typeof query.q === 'string' ? query.q : '',
    lifecycleStatus: normalizeCardLifecycleFilterValue(
      typeof query.lifecycle_status === 'string' ? query.lifecycle_status : undefined,
    ),
    cardPool: normalizeCardPool(query.card_pool),
    cardRoleMatch: query.card_role_match === 'all' ? 'all' : 'any',
    cardRoleKeys: readCardRoleValues(query.card_roles),
    cardRoleExcludeKeys: query.card_role_exclude === undefined
      ? ['hero']
      : readCardRoleValues(query.card_role_exclude),
    cardFactionMatch: query.card_faction_match === 'all' ? 'all' : 'any',
    cardFactionKeys: readCardFactionValues(query.card_factions),
    cardFactionExcludeKeys: readCardFactionValues(query.card_faction_exclude),
    keywordMatch: query.keyword_match === 'all' ? 'all' : 'any',
    tagMatch: query.tag_match === 'all' ? 'all' : 'any',
    typeMatch: query.type_match === 'all' ? 'all' : 'any',
    manaSymbolMatch: query.mana_family_match === 'all' || query.mana_symbol_match === 'all' ? 'all' : 'any',
    affinitySymbolMatch: query.affinity_symbol_match === 'all' ? 'all' : 'any',
    devotionSymbolMatch: query.devotion_symbol_match === 'all' ? 'all' : 'any',
    otherSymbolMatch: query.other_symbol_match === 'all' ? 'all' : 'any',
    templateId: typeof query.template_id === 'string' ? query.template_id : '',
    manaCostMin: typeof query.mana_cost_min === 'string' ? query.mana_cost_min : '',
    manaCostMax: typeof query.mana_cost_max === 'string' ? query.mana_cost_max : '',
    attackMin: typeof query.attack_min === 'string' ? query.attack_min : '',
    attackMax: typeof query.attack_max === 'string' ? query.attack_max : '',
    healthMin: typeof query.health_min === 'string' ? query.health_min : '',
    healthMax: typeof query.health_max === 'string' ? query.health_max : '',
    keywordKeys: readQueryValues(query.keyword_keys),
    tagKeys: readQueryValues(query.tag_keys),
    manaSymbolKeys: [
      ...readQueryValues(query.mana_family_keys),
      ...readQueryValues(query.mana_symbol_keys),
    ],
    manaSymbolExcludeKeys: [
      ...readQueryValues(query.mana_family_exclude_keys),
      ...readQueryValues(query.mana_symbol_exclude_keys),
    ],
    affinitySymbolKeys: readQueryValues(query.affinity_symbol_keys),
    affinitySymbolExcludeKeys: readQueryValues(query.affinity_symbol_exclude_keys),
    devotionSymbolKeys: readQueryValues(query.devotion_symbol_keys),
    devotionSymbolExcludeKeys: readQueryValues(query.devotion_symbol_exclude_keys),
    otherSymbolKeys: readQueryValues(query.other_symbol_keys),
    otherSymbolExcludeKeys: readQueryValues(query.other_symbol_exclude_keys),
    typeKeys: readQueryValues(query.type_keys),
    typeExcludeKeys: readQueryValues(query.type_exclude_keys),
  });

export const buildCardFilterRouteQuery = (state: CardFilterState): LocationQueryRaw => {
  const normalized = normalizeCardFilterState(state);
  const query: LocationQueryRaw = {};

  if (normalized.query) query.q = normalized.query;
  if (normalized.lifecycleStatus !== DEFAULT_CARD_LIFECYCLE_FILTER)
    query.lifecycle_status = normalized.lifecycleStatus;
  if (normalized.cardPool !== 'player') query.card_pool = normalized.cardPool;
  if (normalized.cardRoleMatch === 'all') query.card_role_match = 'all';
  if (normalized.cardRoleKeys.length > 0) query.card_roles = normalized.cardRoleKeys;
  if (normalized.cardRoleExcludeKeys.length === 0) query.card_role_exclude = 'none';
  else if (
    normalized.cardRoleExcludeKeys.length !== 1
    || normalized.cardRoleExcludeKeys[0] !== 'hero'
  ) query.card_role_exclude = normalized.cardRoleExcludeKeys;
  if (normalized.cardFactionMatch === 'all') query.card_faction_match = 'all';
  if ((normalized.cardFactionKeys?.length ?? 0) > 0) query.card_factions = normalized.cardFactionKeys;
  if ((normalized.cardFactionExcludeKeys?.length ?? 0) > 0) {
    query.card_faction_exclude = normalized.cardFactionExcludeKeys;
  }
  if (normalized.keywordMatch === 'all') query.keyword_match = 'all';
  if (normalized.tagMatch === 'all') query.tag_match = 'all';
  if (normalized.typeMatch === 'all') query.type_match = 'all';
  if (normalized.manaSymbolMatch === 'all') query.mana_family_match = 'all';
  if (normalized.affinitySymbolMatch === 'all') query.affinity_symbol_match = 'all';
  if (normalized.devotionSymbolMatch === 'all') query.devotion_symbol_match = 'all';
  if (normalized.otherSymbolMatch === 'all') query.other_symbol_match = 'all';
  if (normalized.templateId) query.template_id = normalized.templateId;
  if (normalized.manaCostMin) query.mana_cost_min = normalized.manaCostMin;
  if (normalized.manaCostMax) query.mana_cost_max = normalized.manaCostMax;
  if (normalized.attackMin) query.attack_min = normalized.attackMin;
  if (normalized.attackMax) query.attack_max = normalized.attackMax;
  if (normalized.healthMin) query.health_min = normalized.healthMin;
  if (normalized.healthMax) query.health_max = normalized.healthMax;
  if (normalized.keywordKeys.length > 0) query.keyword_keys = normalized.keywordKeys;
  if (normalized.tagKeys.length > 0) query.tag_keys = normalized.tagKeys;
  if (normalized.manaSymbolKeys.length > 0) query.mana_family_keys = normalized.manaSymbolKeys;
  if (normalized.manaSymbolExcludeKeys.length > 0)
    query.mana_family_exclude_keys = normalized.manaSymbolExcludeKeys;
  if (normalized.affinitySymbolKeys.length > 0)
    query.affinity_symbol_keys = normalized.affinitySymbolKeys;
  if (normalized.affinitySymbolExcludeKeys.length > 0)
    query.affinity_symbol_exclude_keys = normalized.affinitySymbolExcludeKeys;
  if (normalized.devotionSymbolKeys.length > 0)
    query.devotion_symbol_keys = normalized.devotionSymbolKeys;
  if (normalized.devotionSymbolExcludeKeys.length > 0)
    query.devotion_symbol_exclude_keys = normalized.devotionSymbolExcludeKeys;
  if (normalized.otherSymbolKeys.length > 0) query.other_symbol_keys = normalized.otherSymbolKeys;
  if (normalized.otherSymbolExcludeKeys.length > 0)
    query.other_symbol_exclude_keys = normalized.otherSymbolExcludeKeys;
  if (normalized.typeKeys.length > 0) query.type_keys = normalized.typeKeys;
  if (normalized.typeExcludeKeys.length > 0) query.type_exclude_keys = normalized.typeExcludeKeys;

  return query;
};

export const buildCardFilterRouteSearchParams = (state: CardFilterState): URLSearchParams => {
  const params = new URLSearchParams();
  const query = buildCardFilterRouteQuery(state);

  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((entry) => params.append(key, String(entry)));
    } else if (value !== undefined) {
      params.set(key, String(value));
    }
  });

  return params;
};

export const getCardFilterSignature = (state: CardFilterState): string =>
  buildCardFilterRouteSearchParams(state).toString();

export const sameCardFilterState = (left: CardFilterState, right: CardFilterState): boolean =>
  getCardFilterSignature(left) === getCardFilterSignature(right);
