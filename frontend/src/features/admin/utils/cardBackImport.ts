import type { CardListItem } from '@/domain/cards/types';
import type { CardBackRecord } from '@/domain/card-backs/types';

export const cardBackLabel = (filename: string): string =>
  filename.replace(/\.[^.]+$/, '').replace(/[_-]/g, ' ').trim() || 'Card Back';

const matchKey = (name: string): string =>
  name.replace(/[_-]/g, ' ').trim().replace(/\s+/g, ' ').toLocaleLowerCase();

export const suggestHero = (filename: string, heroes: CardListItem[]): CardListItem | null => {
  const key = matchKey(cardBackLabel(filename));
  const matches = heroes.filter((hero) => matchKey(hero.name) === key);
  return matches.length === 1 ? matches[0] ?? null : null;
};

export type CardBackUsage = 'all' | 'overrides' | 'defaults' | 'unused';
export const matchesCardBackUsage = (asset: CardBackRecord, usage: CardBackUsage): boolean => {
  const defaults = asset.default_for_pools.length + asset.default_for_roles.length
    + asset.default_for_factions.length > 0;
  if (usage === 'defaults') return defaults;
  if (usage === 'overrides') return asset.override_card_count > 0;
  if (usage === 'unused') return !defaults && asset.override_card_count === 0;
  return true;
};

export const cardBackFileError = (file: File): string => {
  if (!/\.(png|jpe?g|webp|bmp|tiff?)$/i.test(file.name)) return 'Choose PNG, JPG, WebP, BMP, or TIFF.';
  return file.size === 0 ? 'This file is empty.' : '';
};
