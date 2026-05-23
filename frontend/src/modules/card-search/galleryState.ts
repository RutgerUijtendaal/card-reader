import type { PaginatedCardsResponse } from '@/modules/card-detail/types';

type IdentifiableCard = {
  id: string;
};

export type GalleryPageState<TCard extends IdentifiableCard> = {
  cards: TCard[];
  count: number;
  nextPage: number | null;
  page: number;
  pageSize: number;
};

export const createEmptyGalleryPageState = <TCard extends IdentifiableCard>(): GalleryPageState<TCard> => ({
  cards: [],
  count: 0,
  nextPage: 1,
  page: 0,
  pageSize: 72,
});

export const replaceGalleryPage = <TCard extends IdentifiableCard>(
  response: PaginatedCardsResponse<TCard>,
): GalleryPageState<TCard> => ({
  cards: response.results,
  count: response.count,
  nextPage: response.next_page,
  page: response.page,
  pageSize: response.page_size,
});

export const appendGalleryPage = <TCard extends IdentifiableCard>(
  current: GalleryPageState<TCard>,
  response: PaginatedCardsResponse<TCard>,
  identity: ((card: TCard) => string) | null = null,
): GalleryPageState<TCard> => {
  const readIdentity = identity ?? ((card: TCard) => card.id);
  const seen = new Set(current.cards.map((card) => readIdentity(card)));
  const appended = response.results.filter((card) => !seen.has(readIdentity(card)));
  return {
    cards: [...current.cards, ...appended],
    count: response.count,
    nextPage: response.next_page,
    page: response.page,
    pageSize: response.page_size,
  };
};

export const isLatestGalleryRequest = (requestId: number, latestRequestId: number): boolean =>
  requestId === latestRequestId;
