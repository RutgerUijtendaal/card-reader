export const CARD_FACTION_OPTIONS = [
  { value: 'order', label: 'Order' },
  { value: 'blood', label: 'Blood' },
  { value: 'dark', label: 'Dark' },
  { value: 'metal', label: 'Metal' },
] as const;

export type CardFaction = (typeof CARD_FACTION_OPTIONS)[number]['value'];

const CARD_FACTION_SET: ReadonlySet<string> = new Set(
  CARD_FACTION_OPTIONS.map((option) => option.value),
);

export const isCardFaction = (value: string): value is CardFaction =>
  CARD_FACTION_SET.has(value);

export const cardFactionLabel = (faction: CardFaction): string =>
  CARD_FACTION_OPTIONS.find((option) => option.value === faction)?.label ?? faction;

export const displayCardFactionLabels = (factions: readonly CardFaction[]): string[] =>
  factions.length > 0 ? factions.map(cardFactionLabel) : ['No faction'];
