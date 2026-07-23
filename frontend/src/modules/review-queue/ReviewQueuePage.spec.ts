import { createApp, nextTick, ref } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import ReviewQueuePage from '@/modules/review-queue/ReviewQueuePage.vue';

const { apiGet, apiPatch, decrementOpenParseFlagItemCount, loadReviewSummary } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  decrementOpenParseFlagItemCount: vi.fn(),
  loadReviewSummary: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  api: {
    get: apiGet,
    patch: apiPatch,
  },
  toAbsoluteApiUrl: (value: string) => value,
}));

vi.mock('@/composables/useCardCollection', () => ({
  useCardCollection: () => ({
    cards: ref([]),
    isLoadingInitial: ref(false),
    nextPage: ref(null),
    searchCards: vi.fn(),
    loadNextPage: vi.fn(),
  }),
}));

vi.mock('@/composables/useReviewSummary', () => ({
  useReviewSummary: () => ({
    decrementOpenParseFlagItemCount,
    loadReviewSummary,
  }),
}));

const overallItem = {
  id: 'overall-item',
  flag_id: 'flag-1',
  status: 'open',
  property_key: 'overall',
  captured_current_value: '',
  expected_value: '',
  note: 'Give this card a clearer role.',
  created_at: '2026-07-23T10:00:00Z',
  updated_at: '2026-07-23T10:00:00Z',
  review_note: '',
  reviewed_at: null,
  reviewed_by: null,
};

const nameItem = {
  ...overallItem,
  id: 'name-item',
  property_key: 'name',
  captured_current_value: 'Old Name',
  expected_value: 'New Name',
  note: 'The parsed name is wrong.',
  created_at: '2026-07-23T10:01:00Z',
};

const pagePayload = () => ({
  count: 1,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 25,
  results: [
    {
      id: 'flag-1',
      note: 'Shared context.',
      created_at: '2026-07-23T10:00:00Z',
      updated_at: '2026-07-23T10:01:00Z',
      submitted_by: { id: 'user-1', username: 'reporter' },
      card: { id: 'card-1', label: 'Card One', name: 'Card One', image_url: null },
      version: {
        id: 'version-1',
        version_number: 1,
        is_latest: true,
        content_version: null,
      },
      items: [overallItem, nameItem],
    },
  ],
});

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
};

const mountPage = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/review', component: ReviewQueuePage },
      { path: '/cards/:id/edit', component: { template: '<div />' } },
    ],
  });
  await router.push('/review?view=flags&status=open');
  await router.isReady();
  const app = createApp(ReviewQueuePage);
  app.use(router);
  app.mount(container);
  await flushPromises();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('ReviewQueuePage parse flags', () => {
  beforeEach(() => {
    apiGet.mockResolvedValue({ data: pagePayload() });
    apiPatch.mockResolvedValue({ data: { ...overallItem, status: 'dismissed' } });
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('renders overall suggestions without value comparison and routes them without field focus', async () => {
    const mounted = await mountPage();
    const itemSections = Array.from(mounted.container.querySelectorAll('.border-t.pt-3'));
    const overallSection = itemSections.find((section) =>
      section.textContent?.includes('Overall card suggestion'),
    );
    const nameSection = itemSections.find((section) =>
      section.textContent?.includes('The parsed name is wrong.'),
    );

    expect(overallSection?.textContent).toContain('Give this card a clearer role.');
    expect(overallSection?.textContent).not.toContain('Reported Value');
    expect(nameSection?.textContent).toContain('Reported Value');
    expect(nameSection?.textContent).toContain('Old Name');
    expect(nameSection?.textContent).toContain('New Name');

    const editorLinks = Array.from(mounted.container.querySelectorAll('a')).filter(
      (link) => link.textContent?.trim() === 'Open Editor',
    );
    expect(editorLinks[0]?.getAttribute('href')).toContain('version_id=version-1');
    expect(editorLinks[0]?.getAttribute('href')).not.toContain('property_key');
    expect(editorLinks[1]?.getAttribute('href')).toContain('property_key=name');
    mounted.unmount();
  });

  test('keeps overall suggestions in the existing resolve and dismiss workflow', async () => {
    const mounted = await mountPage();
    const dismissButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Dismiss',
    );
    expect(dismissButton).toBeInstanceOf(HTMLButtonElement);
    (dismissButton as HTMLButtonElement).click();
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/review/parse-flags/items/overall-item', {
      status: 'dismissed',
    });
    expect(decrementOpenParseFlagItemCount).toHaveBeenCalledOnce();
    expect(mounted.container.textContent).not.toContain('Give this card a clearer role.');
    expect(mounted.container.textContent).toContain('The parsed name is wrong.');
    mounted.unmount();
  });
});
