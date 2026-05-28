import type { MetadataOption, SymbolFilterOption } from '@/modules/card-detail/types';
import type { MetadataFavoriteGroup } from '@/modules/card-filters/useMetadataFilterFavorites';

export type MatchMode = 'any' | 'all';
export type LifecycleFilterValue = 'active' | 'deprecated' | 'all';
export type SymbolFilterTriState = 'off' | 'include' | 'exclude';
export type CardFilterSectionKey =
  | 'mana'
  | 'types'
  | 'affinity'
  | 'devotion'
  | 'generic'
  | 'keywords'
  | 'tags';

export type CardFilterSectionsState = {
  selectedManaTypeSymbolIds: string[];
  lifecycleStatus: LifecycleFilterValue;
  onUpdateLifecycleStatus: (value: LifecycleFilterValue) => void;
  onUpdateSelectedManaTypeSymbolIds: (value: string[]) => void;
  excludedManaTypeSymbolIds: string[];
  onUpdateExcludedManaTypeSymbolIds: (value: string[]) => void;
  manaSymbolMatch: MatchMode;
  onUpdateManaSymbolMatch: (value: MatchMode) => void;
  manaTypeOptions: SymbolFilterOption[];
  manaCostMin: string;
  onUpdateManaCostMin: (value: string) => void;
  manaCostMax: string;
  onUpdateManaCostMax: (value: string) => void;
  resetManaGroup: () => void;
  selectedTypeIds: string[];
  onUpdateSelectedTypeIds: (value: string[]) => void;
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
