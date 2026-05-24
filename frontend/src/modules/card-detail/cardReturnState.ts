import type { LocationQuery, RouteLocationRaw } from 'vue-router';
import { buildGalleryLocation } from '@/modules/card-search/galleryNavigation';
import { buildAdminReturnLocation, isAdminReturnQuery } from '@/modules/admin/adminRouteState';
import { buildDeckReturnLocation, isDeckReturnQuery } from '@/modules/decks/deckRouteState';

export const buildCardReturnLocation = (query: LocationQuery): RouteLocationRaw => {
  if (isAdminReturnQuery(query)) {
    return buildAdminReturnLocation(query);
  }
  if (isDeckReturnQuery(query)) {
    return buildDeckReturnLocation(query);
  }
  return buildGalleryLocation(query);
};

export const getCardReturnLabel = (query: LocationQuery): 'Gallery' | 'Admin' | 'Deck' => {
  if (isAdminReturnQuery(query)) {
    return 'Admin';
  }
  if (isDeckReturnQuery(query)) {
    return 'Deck';
  }
  return 'Gallery';
};
