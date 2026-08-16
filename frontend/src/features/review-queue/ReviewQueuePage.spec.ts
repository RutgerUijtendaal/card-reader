import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import ReviewQueuePage from '@/features/review-queue/ReviewQueuePage.vue';

const {
  apiGet,
  apiPatch,
  decrementOpenClassificationReviewCount,
  decrementOpenParseFlagItemCount,
  loadReviewSummary,
} = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  decrementOpenClassificationReviewCount: vi.fn(),
  decrementOpenParseFlagItemCount: vi.fn(),
  loadReviewSummary: vi.fn(),
}));

vi.mock('@/shared/api/client', () => ({
  api: { get: apiGet, patch: apiPatch },
  toAbsoluteApiUrl: (value: string) => value,
}));

vi.mock('@/domain/review/composables/useReviewSummary', () => ({
  useReviewSummary: () => ({
    decrementOpenClassificationReviewCount,
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

const page = <T>(results: T[]) => ({
  count: results.length,
  next_page: null,
  previous_page: null,
  page: 1,
  page_size: 25,
  results,
});

const flagPayload = () =>
  page([
    {
      id: 'flag-1',
      note: 'Shared context.',
      created_at: '2026-07-23T10:00:00Z',
      updated_at: '2026-07-23T10:01:00Z',
      submitted_by: { id: 'user-1', username: 'reporter' },
      card: {
        id: 'card-1',
        label: 'Card One',
        name: 'Card One',
        card_pool: 'player',
        card_roles: [],
        card_factions: [],
        card_mana_families: [],
        image_url: null,
      },
      version: {
        id: 'version-1',
        version_number: 1,
        is_latest: true,
        content_version: null,
      },
      items: [overallItem, nameItem],
    },
  ]);

const classificationItem = {
  id: 'classification-1',
  status: 'open',
  created_at: '2026-08-16T10:00:00Z',
  updated_at: '2026-08-16T10:00:00Z',
  review_note: '',
  reviewed_at: null,
  reviewed_by: null,
  import_job_id: 'job-1',
  import_item_id: 'import-item-1',
  card: {
    id: 'card-2',
    label: 'Changed Card',
    name: 'Changed Card',
    card_pool: 'evil',
    card_roles: ['event'],
    card_factions: ['dark'],
    card_mana_families: ['occult'],
    image_url: '/cards/card-2/versions/version-2/image',
  },
  version: {
    id: 'version-2',
    version_number: 2,
    is_latest: true,
    content_version: { id: 'content-1', version_number: '16.2.0' },
  },
  existing_classification: {
    card_pool: 'evil',
    card_roles: [],
    card_factions: ['order'],
    card_mana_families: ['arcane'],
  },
  inferred_classification: {
    card_pool: 'evil',
    card_roles: ['event'],
    card_factions: ['dark'],
    card_mana_families: ['occult'],
  },
  inference_evidence: {
    roles: {
      mode: 'automatic',
      matched_tag_sources: [{ id: 'tag-event', key: 'event' }],
    },
    factions: {
      mode: 'automatic',
      matched_type_sources: [{ id: 'type-dark', key: 'dark' }],
    },
    mana_families: {
      mode: 'automatic',
      matched_symbol_sources: [{ id: 'symbol-occult', key: 'occult-mana' }],
    },
  },
};

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
};

const mountPage = async (location = '/review') => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/review', component: ReviewQueuePage },
      { path: '/cards/:id/edit', component: { template: '<div />' } },
    ],
  });
  await router.push(location);
  await router.isReady();
  const app = createApp(ReviewQueuePage);
  app.use(router);
  app.mount(container);
  await flushPromises();
  return {
    container,
    router,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('ReviewQueuePage', () => {
  beforeEach(() => {
    apiGet.mockImplementation((url: string) =>
      Promise.resolve({
        data: url.startsWith('/review/classification-items')
          ? page([classificationItem])
          : flagPayload(),
      }),
    );
    apiPatch.mockImplementation((url: string) =>
      Promise.resolve({
        data: url.startsWith('/review/classification-items')
          ? { ...classificationItem, status: 'dismissed' }
          : { ...overallItem, status: 'dismissed' },
      }),
    );
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  test('defaults to classification and shows captured, inferred, current, and source evidence', async () => {
    const mounted = await mountPage();

    expect(apiGet).toHaveBeenCalledWith(
      '/review/classification-items?status=open&page=1&page_size=25',
    );
    expect(mounted.container.textContent).toContain('Existing when imported');
    expect(mounted.container.textContent).toContain('Inferred from this version');
    expect(mounted.container.textContent).toContain('Current Card');
    expect(mounted.container.textContent).toContain('Role: event');
    expect(mounted.container.textContent).toContain('Faction: dark');
    expect(mounted.container.textContent).toContain('Mana: occult-mana');
    const openCard = Array.from(mounted.container.querySelectorAll('a')).find(
      (link) => link.textContent?.trim() === 'Open Card',
    );
    expect(openCard?.getAttribute('href')).toContain('tab=card');
    expect(openCard?.getAttribute('href')).toContain('review_view=classification');
    mounted.unmount();
  });

  test('keeps the existing classification through an explicit terminal action', async () => {
    const mounted = await mountPage();
    const keepButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.trim() === 'Keep Existing',
    );
    (keepButton as HTMLButtonElement).click();
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/review/classification-items/classification-1', {
      status: 'dismissed',
    });
    expect(decrementOpenClassificationReviewCount).toHaveBeenCalledOnce();
    expect(mounted.container.textContent).not.toContain('Changed Card');
    mounted.unmount();
  });

  test('preserves parse-flag comparison and editor focus behavior', async () => {
    const mounted = await mountPage('/review?view=flags&status=open');
    const itemSections = Array.from(mounted.container.querySelectorAll('.border-t.pt-3'));
    const overallSection = itemSections.find((section) =>
      section.textContent?.includes('Overall card suggestion'),
    );
    const nameSection = itemSections.find((section) =>
      section.textContent?.includes('The parsed name is wrong.'),
    );

    expect(overallSection?.textContent).not.toContain('Reported Value');
    expect(nameSection?.textContent).toContain('Old Name');
    expect(nameSection?.textContent).toContain('New Name');
    const editorLinks = Array.from(mounted.container.querySelectorAll('a')).filter(
      (link) => link.textContent?.trim() === 'Open Editor',
    );
    expect(editorLinks[0]?.getAttribute('href')).not.toContain('property_key');
    expect(editorLinks[1]?.getAttribute('href')).toContain('property_key=name');
    mounted.unmount();
  });

  test('switches from flags to the global classification queue', async () => {
    const mounted = await mountPage('/review?view=flags&status=open');
    const classificationButton = Array.from(mounted.container.querySelectorAll('button')).find(
      (button) => button.textContent?.includes('Classification'),
    );
    classificationButton?.click();
    await flushPromises();

    await vi.waitFor(() => {
      expect(mounted.router.currentRoute.value.query.view).toBe('classification');
    });
    expect(classificationButton?.getAttribute('aria-current')).toBe('page');
    expect(apiGet).toHaveBeenCalledWith(
      '/review/classification-items?status=open&page=1&page_size=25',
    );
    mounted.unmount();
  });
});
