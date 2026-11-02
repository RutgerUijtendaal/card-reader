import { useLocalStorage } from '@vueuse/core';

export type CardCollectionLayout = 'list' | 'images';

const isCardCollectionLayout = (value: unknown): value is CardCollectionLayout =>
  value === 'list' || value === 'images';

/** The deck and Encounter detail pages share one remembered choice between decklist and images. */
export const useCardCollectionLayout = () => {
  const layout = useLocalStorage<CardCollectionLayout>(
    'card-reader.collection-detail-layout',
    'images',
    {
      serializer: {
        read: (raw) => (isCardCollectionLayout(raw) ? raw : 'images'),
        write: (value) => value,
      },
    },
  );
  return { layout };
};
