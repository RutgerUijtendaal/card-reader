import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardBacksAdminView from '@/modules/admin/views/CardBacksAdminView.vue';
import type { CardBackRecord } from '@/modules/admin/types';

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
  toAbsoluteApiUrl: (url: string) => url,
}));

vi.mock('vue-sonner', () => ({
  toast: {
    error: vi.fn(),
    success: toastSuccess,
  },
}));

const buildCardBack = (overrides: Partial<CardBackRecord> = {}): CardBackRecord => ({
  id: 'card-back-1',
  label: 'Default Back',
  original_filename: 'back.png',
  source_file: 'uploads/card-backs/back.png',
  stored_path: 'images/back.webp',
  width: 63,
  height: 88,
  checksum: 'checksum',
  is_current: true,
  image_url: '/card-images/images/back.webp',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const flushPromises = async (): Promise<void> => {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
};

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);

  const app = createApp(CardBacksAdminView);
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

describe('CardBacksAdminView', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('loads history and renders the current card back preview', async () => {
    apiGet.mockResolvedValue({ data: [buildCardBack()] });

    const mounted = await mountView();

    expect(apiGet).toHaveBeenCalledWith('/admin/card-backs');
    expect(mounted.container.textContent).toContain('Default Back');
    expect(mounted.container.textContent).toContain('Current');
    expect(mounted.container.querySelector('img')?.getAttribute('src')).toBe('/card-images/images/back.webp');

    mounted.unmount();
  });

  test('uploads a selected card back and refreshes history', async () => {
    apiGet
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [buildCardBack({ label: 'Uploaded Back' })] });
    apiPost.mockResolvedValue({ data: buildCardBack({ label: 'Uploaded Back' }) });

    const mounted = await mountView();
    const labelInput = mounted.container.querySelector<HTMLInputElement>('input[placeholder="Default card back"]');
    const fileInput = mounted.container.querySelector<HTMLInputElement>('input[type="file"]');
    const submitButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Upload And Set Current'),
    );
    if (!(labelInput instanceof HTMLInputElement) || !(fileInput instanceof HTMLInputElement) || !(submitButton instanceof HTMLButtonElement)) {
      throw new Error('expected upload controls');
    }

    labelInput.value = 'Uploaded Back';
    labelInput.dispatchEvent(new Event('input', { bubbles: true }));
    Object.defineProperty(fileInput, 'files', {
      value: [new File(['image'], 'uploaded.png', { type: 'image/png' })],
      configurable: true,
    });
    Object.defineProperty(fileInput, 'value', {
      value: 'C:\\fakepath\\uploaded.png',
      writable: true,
      configurable: true,
    });
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();

    submitButton.click();
    await flushPromises();
    await nextTick();

    expect(apiPost).toHaveBeenCalledWith('/admin/card-backs/upload', expect.any(FormData));
    expect(apiGet).toHaveBeenCalledTimes(2);
    expect(fileInput.value).toBe('');
    expect(toastSuccess).toHaveBeenCalledWith('Card back uploaded.');

    mounted.unmount();
  });

  test('activates an older card back', async () => {
    apiGet
      .mockResolvedValueOnce({
        data: [
          buildCardBack(),
          buildCardBack({
            id: 'card-back-2',
            label: 'Older Back',
            is_current: false,
            image_url: '/card-images/images/older.webp',
          }),
        ],
      })
      .mockResolvedValueOnce({
        data: [
          buildCardBack({ is_current: false }),
          buildCardBack({
            id: 'card-back-2',
            label: 'Older Back',
            is_current: true,
            image_url: '/card-images/images/older.webp',
          }),
        ],
      });
    apiPost.mockResolvedValue({ data: buildCardBack({ id: 'card-back-2', is_current: true }) });

    const mounted = await mountView();
    const activateButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Set Current') && !(button as HTMLButtonElement).disabled,
    );
    if (!(activateButton instanceof HTMLButtonElement)) {
      throw new Error('expected activate button');
    }

    activateButton.click();
    await flushPromises();
    await nextTick();

    expect(apiPost).toHaveBeenCalledWith('/admin/card-backs/card-back-2/activate');
    expect(toastSuccess).toHaveBeenCalledWith('Current card back updated.');

    mounted.unmount();
  });
});
