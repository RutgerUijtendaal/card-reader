import { effectScope } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { useCardPublicDetailState } from '@/modules/card-detail/composables/useCardPublicDetailState';

const { apiGet, replaceRoute, route } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  replaceRoute: vi.fn(),
  route: {
    params: { id: 'card-1' },
    query: { version_id: 'version-2', return_to: 'gallery' },
  },
}));

vi.mock('@vueuse/core', () => ({
  onKeyStroke: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({ push: vi.fn(), replace: replaceRoute }),
}));

vi.mock('@/api/client', () => ({
  api: { get: apiGet },
  toAbsoluteApiUrl: (value: string) => value,
}));

vi.mock('@/modules/auth/authStore', () => ({
  useAuthStore: () => ({ canAccessStaffRoutes: false }),
}));

vi.mock('@/composables/card-gallery/galleryNavigation', () => ({
  useGalleryCardNavigation: () => ({
    hasGalleryContext: { value: false },
    previousCardId: { value: null },
    nextCardId: { value: null },
    hasMoreResults: { value: false },
    isLoadingMoreCards: { value: false },
    positionLabel: { value: '' },
    goToPreviousCard: vi.fn(),
    goToNextCard: vi.fn(),
  }),
}));

describe('useCardPublicDetailState version navigation', () => {
  afterEach(() => {
    vi.clearAllMocks();
    route.query = { version_id: 'version-2', return_to: 'gallery' };
  });

  test('selects a requested version and keeps later selections in the URL', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url.endsWith('/generations')) {
        return Promise.resolve({
          data: [
            { version_id: 'version-1', is_latest: true },
            { version_id: 'version-2', is_latest: false },
          ],
        });
      }
      if (url === '/cards/filters') {
        return Promise.resolve({ data: { symbols: [] } });
      }
      return Promise.resolve({ data: { id: 'card-1' } });
    });

    const scope = effectScope();
    const state = scope.run(() => useCardPublicDetailState());
    expect(state).toBeDefined();
    await state?.loadCard();

    expect(state?.selectedVersionId.value).toBe('version-2');

    state?.selectVersion('version-1');
    expect(replaceRoute).toHaveBeenCalledWith({
      query: {
        version_id: 'version-1',
        return_to: 'gallery',
      },
    });
    scope.stop();
  });
});
