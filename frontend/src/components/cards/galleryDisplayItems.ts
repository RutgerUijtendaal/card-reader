import type { GalleryItem } from '@/modules/card-detail/types';

export type LoadingShimGalleryItem = {
  id: string;
  result_type: 'loading_shim';
};

export type GalleryDisplayItem = GalleryItem | LoadingShimGalleryItem;

export const createLoadingShimItems = (count: number): LoadingShimGalleryItem[] =>
  Array.from({ length: Math.max(0, count) }, (_, index) => ({
    id: `loading-shim-${index + 1}`,
    result_type: 'loading_shim',
  }));
