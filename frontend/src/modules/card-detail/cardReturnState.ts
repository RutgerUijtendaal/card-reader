import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { buildGalleryLocation } from '@/modules/card-search/galleryNavigation';
import { buildDeckReturnLocation, isDeckReturnQuery } from '@/modules/decks/deckRouteState';
import { buildSettingsReturnLocation, isSettingsReturnQuery } from '@/modules/settings/settingsRouteState';

export const buildCardReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  if (isSettingsReturnQuery(query)) {
    return buildSettingsReturnLocation(query);
  }
  if (isDeckReturnQuery(query)) {
    return buildDeckReturnLocation(query);
  }
  return buildGalleryLocation(query);
};

export const getCardReturnLabel = (query: LocationQuery): 'Gallery' | 'Settings' | 'Deck' => {
  if (isSettingsReturnQuery(query)) {
    return 'Settings';
  }
  if (isDeckReturnQuery(query)) {
    return 'Deck';
  }
  return 'Gallery';
};
