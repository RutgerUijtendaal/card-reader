export const MANA_FAMILY_OPTIONS = [
  { value: 'arcane', label: 'Arcane' },
  { value: 'dark', label: 'Dark' },
  { value: 'divine', label: 'Divine' },
  { value: 'martial', label: 'Martial' },
  { value: 'occult', label: 'Occult' },
  { value: 'primal', label: 'Primal' },
] as const;

export type ManaFamily = (typeof MANA_FAMILY_OPTIONS)[number]['value'];

const MANA_FAMILY_SET: ReadonlySet<string> = new Set(
  MANA_FAMILY_OPTIONS.map((option) => option.value),
);

export const isManaFamily = (value: string): value is ManaFamily =>
  MANA_FAMILY_SET.has(value);

export const manaFamilyLabel = (family: ManaFamily): string =>
  MANA_FAMILY_OPTIONS.find((option) => option.value === family)?.label ?? family;

export const displayManaFamilyLabels = (families: readonly ManaFamily[]): string[] =>
  families.length > 0 ? families.map(manaFamilyLabel) : ['Colorless'];
