import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import MaintenanceAdminView from '@/features/admin/views/MaintenanceAdminView.vue';

const { apiGet, apiPost, toastSuccess } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock('@/shared/api/client', () => ({
  api: {
    get: apiGet,
    post: apiPost,
  },
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: toastSuccess,
  },
}));

vi.mock('@/domain/cards/components/filters/CardFilterSections.vue', () => ({
  default: {
    template: '<div />',
  },
}));

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
};

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const app = createApp(MaintenanceAdminView);
  app.mount(container);
  await flushPromises();
  await nextTick();

  return {
    container,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

describe('MaintenanceAdminView', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('runs card image WebP conversion from maintenance action', async () => {
    apiGet.mockResolvedValue({
      data: {
        keywords: [],
        tags: [],
        symbols: [],
        types: [],
      },
    });
    apiPost.mockResolvedValue({
      data: {
        message: 'Converted 2 card images to WebP.',
        removed_paths: [],
        converted: 2,
        already_webp: 1,
        missing: 0,
        failed: 0,
        bytes_before: 2000,
        bytes_after: 500,
        failures: [],
      },
    });

    const mounted = await mountView();
    const convertButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Convert Card Images To WebP'),
    );
    if (!(convertButton instanceof HTMLButtonElement)) {
      throw new Error('expected conversion button');
    }

    convertButton.click();
    await flushPromises();
    await nextTick();

    expect(apiPost).toHaveBeenCalledWith('/admin/maintenance/convert-card-images-to-webp');
    expect(toastSuccess).toHaveBeenCalledWith('Converted 2 card images to WebP.');

    mounted.unmount();
  });

  test('keeps empty filtered reparses inactive and sends selected filters globally', async () => {
    apiGet.mockImplementation((url: string) => {
      if (url === '/cards/filters') {
        return Promise.resolve({
          data: {
            keywords: [],
            tags: [],
            symbols: [],
            types: [],
          },
        });
      }
      if (url.startsWith('/cards?')) {
        return Promise.resolve({
          data: {
            count: 3,
            page: 1,
            page_size: 1,
            results: [],
          },
        });
      }
      throw new Error(`Unexpected GET ${url}`);
    });
    apiPost.mockResolvedValue({
      data: {
        message: 'Queued 3 latest card images.',
        removed_paths: [],
      },
    });

    const mounted = await mountView();
    const buttons = Array.from(mounted.container.querySelectorAll('button'));
    const previewButton = buttons.find((button) => button.textContent?.includes('Preview Count'));
    const queueButton = buttons.find((button) => button.textContent?.includes('Queue Selection'));
    const showFiltersButton = buttons.find((button) => button.textContent?.includes('Show Filters'));
    if (
      !(previewButton instanceof HTMLButtonElement)
      || !(queueButton instanceof HTMLButtonElement)
      || !(showFiltersButton instanceof HTMLButtonElement)
    ) {
      throw new Error('expected filtered reparse controls');
    }

    expect(previewButton.disabled).toBe(true);
    expect(queueButton.disabled).toBe(true);
    expect(mounted.container.textContent).toContain('No filters selected');

    showFiltersButton.click();
    await nextTick();
    const searchInput = mounted.container.querySelector('input[placeholder^="Name"]');
    if (!(searchInput instanceof HTMLInputElement)) {
      throw new Error('expected filtered reparse search input');
    }
    searchInput.value = 'Shared metadata';
    searchInput.dispatchEvent(new Event('input'));
    await nextTick();

    expect(previewButton.disabled).toBe(false);
    expect(queueButton.disabled).toBe(false);
    expect(mounted.container.textContent).toContain('1 filter selected');

    previewButton.click();
    await flushPromises();
    const previewCall = apiGet.mock.calls.find(
      ([url]) => typeof url === 'string' && url.startsWith('/cards?'),
    );
    expect(previewCall).toBeDefined();
    const previewUrl = new URL(previewCall?.[0] as string, 'http://localhost');
    expect(previewUrl.searchParams.get('q')).toBe('Shared metadata');
    expect(previewUrl.searchParams.has('card_pool')).toBe(false);

    queueButton.click();
    await flushPromises();
    expect(apiPost).toHaveBeenCalledWith(
      '/admin/maintenance/queue-filtered-latest-reparse',
      { q: 'Shared metadata' },
    );

    mounted.unmount();
  });
});
