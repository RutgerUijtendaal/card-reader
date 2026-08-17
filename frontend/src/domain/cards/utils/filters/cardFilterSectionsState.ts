import type { MetadataOption, SymbolFilterOption } from '@/domain/cards/types';
import type { CardLifecycleFilterValue } from '@/domain/cards/utils/filters/cardLifecycle';
import type { MetadataFavoriteGroup } from '@/domain/cards/composables/filters/useMetadataFilterFavorites';
import type { TriStateSelection } from '@/domain/cards/utils/filters/triStateSelection';
import type { CardPool } from '@/domain/cards/cardPools';

export type MatchMode = 'any' | 'all';
export type LifecycleFilterValue = CardLifecycleFilterValue;
export type SymbolFilterTriState = TriStateSelection;
export type CardFilterSectionKey =
  | 'roles'
  | 'factions'
  | 'mana'
  | 'types'
  | 'affinity'
  | 'devotion'
  | 'generic'
  | 'keywords'
  | 'tags';

export type CardFilterSectionsState = {
  cardPool: CardPool;
  onUpdateCardPool: (value: CardPool) => void;
  cardPoolOptions: MetadataOption[];
  selectedCardRoles: string[];
  onUpdateSelectedCardRoles: (value: string[]) => void;
  excludedCardRoles: string[];
  onUpdateExcludedCardRoles: (value: string[]) => void;
  cardRoleMatch: MatchMode;
  onUpdateCardRoleMatch: (value: MatchMode) => void;
  cardRoleOptions: MetadataOption[];
  selectedCardFactions: string[];
  onUpdateSelectedCardFactions: (value: string[]) => void;
  excludedCardFactions: string[];
  onUpdateExcludedCardFactions: (value: string[]) => void;
  cardFactionMatch: MatchMode;
  onUpdateCardFactionMatch: (value: MatchMode) => void;
  cardFactionOptions: MetadataOption[];
  resetCardRoleGroup: () => void;
  resetCardFactionGroup: () => void;
  selectedManaFamilyIds: string[];
  lifecycleStatus: LifecycleFilterValue;
  onUpdateLifecycleStatus: (value: LifecycleFilterValue) => void;
  onUpdateSelectedManaFamilyIds: (value: string[]) => void;
  excludedManaFamilyIds: string[];
  onUpdateExcludedManaFamilyIds: (value: string[]) => void;
  manaFamilyMatch: MatchMode;
  onUpdateManaFamilyMatch: (value: MatchMode) => void;
  manaFamilyOptions: SymbolFilterOption[];
  manaCostMin: string;
  onUpdateManaCostMin: (value: string) => void;
  manaCostMax: string;
  onUpdateManaCostMax: (value: string) => void;
  resetManaGroup: () => void;
  selectedTypeIds: string[];
  onUpdateSelectedTypeIds: (value: string[]) => void;
  excludedTypeIds: string[];
  onUpdateExcludedTypeIds: (value: string[]) => void;
  typeMatch: MatchMode;
  onUpdateTypeMatch: (value: MatchMode) => void;
  typeOptions: MetadataOption[];
  resetTypeGroup: () => void;
  selectedAffinitySymbolIds: string[];
  onUpdateSelectedAffinitySymbolIds: (value: string[]) => void;
  excludedAffinitySymbolIds: string[];
  onUpdateExcludedAffinitySymbolIds: (value: string[]) => void;
  affinitySymbolMatch: MatchMode;
  onUpdateAffinitySymbolMatch: (value: MatchMode) => void;
  affinityTypeOptions: SymbolFilterOption[];
  resetAffinityGroup: () => void;
  selectedDevotionSymbolIds: string[];
  onUpdateSelectedDevotionSymbolIds: (value: string[]) => void;
  excludedDevotionSymbolIds: string[];
  onUpdateExcludedDevotionSymbolIds: (value: string[]) => void;
  devotionSymbolMatch: MatchMode;
  onUpdateDevotionSymbolMatch: (value: MatchMode) => void;
  devotionTypeOptions: SymbolFilterOption[];
  resetDevotionGroup: () => void;
  selectedOtherSymbolIds: string[];
  onUpdateSelectedOtherSymbolIds: (value: string[]) => void;
  excludedOtherSymbolIds: string[];
  onUpdateExcludedOtherSymbolIds: (value: string[]) => void;
  otherSymbolMatch: MatchMode;
  onUpdateOtherSymbolMatch: (value: MatchMode) => void;
  otherSymbolOptions: SymbolFilterOption[];
  resetGenericGroup: () => void;
  attackMin: string;
  onUpdateAttackMin: (value: string) => void;
  attackMax: string;
  onUpdateAttackMax: (value: string) => void;
  healthMin: string;
  onUpdateHealthMin: (value: string) => void;
  healthMax: string;
  onUpdateHealthMax: (value: string) => void;
  selectedKeywordIds: string[];
  onUpdateSelectedKeywordIds: (value: string[]) => void;
  keywordMatch: MatchMode;
  onUpdateKeywordMatch: (value: MatchMode) => void;
  keywordOptions: MetadataOption[];
  keywordFavoriteGroup: MetadataFavoriteGroup;
  keywordFavoriteKeys: string[];
  toggleKeywordFavorite: (key: string) => void;
  resetKeywordGroup: () => void;
  selectedTagIds: string[];
  onUpdateSelectedTagIds: (value: string[]) => void;
  tagMatch: MatchMode;
  onUpdateTagMatch: (value: MatchMode) => void;
  tagOptions: MetadataOption[];
  tagFavoriteGroup: MetadataFavoriteGroup;
  tagFavoriteKeys: string[];
  toggleTagFavorite: (key: string) => void;
  resetTagGroup: () => void;
};
