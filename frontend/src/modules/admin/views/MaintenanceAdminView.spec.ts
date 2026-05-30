import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import MaintenanceAdminView from '@/modules/admin/views/MaintenanceAdminView.vue';

const { apiGet, apiPost, toastSuccess } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock('@/api/client', () => ({
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

vi.mock('@/modules/card-search/components/CardFilterSections.vue', () => ({
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
});
