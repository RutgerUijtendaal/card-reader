import type { MetadataGroupName, ScalarFieldName } from '@/domain/cards/types';

export type ParseFlagPropertyKey = ScalarFieldName | MetadataGroupName | 'overall' | 'other';

export type ParseFlagItemDraft = {
  property_key: ParseFlagPropertyKey;
  expected_value: string;
  note: string;
};

export type ParseFlagCreatePayload = {
  note: string;
  items: ParseFlagItemDraft[];
};

export const parseFlagPropertyLabels: Record<ParseFlagPropertyKey, string> = {
  name: 'Name',
  type_line: 'Type Line',
  mana_cost: 'Mana Cost',
  attack: 'Attack',
  health: 'Health',
  rules_text: 'Rules Text',
  keywords: 'Keywords',
  tags: 'Tags',
  types: 'Types',
  symbols: 'Symbols',
  overall: 'Overall card suggestion',
  other: 'Other',
};
