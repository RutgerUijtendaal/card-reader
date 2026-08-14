export const TEMPLATE_PARSER_TYPE_DEFINITIONS = [
  { key: 'name', label: 'Name' },
  { key: 'name_mana_cost', label: 'Name + mana cost' },
  { key: 'type_tag', label: 'Type + tag' },
  { key: 'rules_text', label: 'Rules text' },
  { key: 'attack', label: 'Attack' },
  { key: 'health', label: 'Health' },
  { key: 'affinity', label: 'Affinity' },
] as const;

export type TemplateParserType = (typeof TEMPLATE_PARSER_TYPE_DEFINITIONS)[number]['key'];

export const TEMPLATE_PARSER_TYPE_KEYS: readonly TemplateParserType[] =
  TEMPLATE_PARSER_TYPE_DEFINITIONS.map(({ key }) => key);

export const TEMPLATE_PARSER_TYPES_HINT = TEMPLATE_PARSER_TYPE_KEYS.join(', ');
