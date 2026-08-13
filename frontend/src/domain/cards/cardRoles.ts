export const STANDARD_CARD_ROLE = 'standard' as const;

export const CARD_ROLE_OPTIONS = [
  { value: 'hero', label: 'Hero' },
  { value: 'boss', label: 'Boss' },
  { value: 'location', label: 'Location' },
  { value: 'boon', label: 'Boon' },
  { value: 'event', label: 'Event' },
  { value: 'shop_item', label: 'Shop Item' },
] as const;

export type CardRole = (typeof CARD_ROLE_OPTIONS)[number]['value'];
export type CardRoleFilter = typeof STANDARD_CARD_ROLE | CardRole;

export const CARD_ROLE_FILTER_VALUES: readonly CardRoleFilter[] = [
  STANDARD_CARD_ROLE,
  ...CARD_ROLE_OPTIONS.map((option) => option.value),
];

const CARD_ROLE_FILTER_VALUE_SET: ReadonlySet<string> = new Set(CARD_ROLE_FILTER_VALUES);

export const isCardRoleFilter = (value: string): value is CardRoleFilter =>
  CARD_ROLE_FILTER_VALUE_SET.has(value);

export const cardRoleLabel = (role: CardRole): string =>
  CARD_ROLE_OPTIONS.find((option) => option.value === role)?.label ?? role;

export const displayCardRoleLabels = (roles: readonly CardRole[]): string[] =>
  roles.length > 0 ? roles.map(cardRoleLabel) : ['Normal'];
