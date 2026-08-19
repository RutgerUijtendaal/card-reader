import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardBacksAdminView from '@/features/admin/views/CardBacksAdminView.vue';
import type { CardBackRecord } from '@/domain/card-backs/types';

Object.defineProperty(URL, 'createObjectURL', {
  configurable: true,
  value: vi.fn(() => 'blob:card-back-preview'),
});
Object.defineProperty(URL, 'revokeObjectURL', {
  configurable: true,
  value: vi.fn(),
});

const { apiGet, apiPost, apiPut, toastSuccess } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  toastSuccess: vi.fn(),
}));

vi.mock('@/shared/api/client', () => ({
  api: { get: apiGet, post: apiPost, put: apiPut },
  toAbsoluteApiUrl: (url: string) => url,
}));
vi.mock('vue-sonner', () => ({ toast: { error: vi.fn(), success: toastSuccess } }));

const buildCardBack = (overrides: Partial<CardBackRecord> = {}): CardBackRecord => ({
  id: 'card-back-1',
  label: 'Default Back',
  original_filename: 'back.png',
  source_file: 'uploads/card-backs/back.png',
  stored_path: 'images/back.webp',
  width: 63,
  height: 88,
  checksum: 'checksum',
  default_for_pools: ['player'],
  override_card_count: 2,
  is_usable: true,
  image_url: '/card-images/images/back.webp',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

const flushPromises = async (): Promise<void> => {
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
  return { container, unmount: () => { app.unmount(); container.remove(); } };
};

const mockLoads = (assets = [buildCardBack()]): void => {
  apiGet.mockImplementation((url: string) => Promise.resolve({
    data: url === '/card-backs/defaults'
      ? { player: assets[0] ?? null, evil: null, neutral: null }
      : assets,
  }));
};

describe('CardBacksAdminView', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('loads pool defaults and the reusable asset library', async () => {
    mockLoads();
    const mounted = await mountView();
    expect(apiGet).toHaveBeenCalledWith('/admin/card-backs');
    expect(apiGet).toHaveBeenCalledWith('/card-backs/defaults');
    expect(mounted.container.textContent).toContain('Default Back');
    expect(mounted.container.textContent).toContain('2 card overrides');
    expect(mounted.container.textContent).not.toContain('back.png');
    expect(mounted.container.textContent).not.toContain('card-back-1');
    expect(mounted.container.textContent).not.toContain('checksum');
    expect(mounted.container.textContent).not.toContain('63 × 88');
    const assetGrid = mounted.container.querySelector('[role="list"][aria-label="Card-back assets"]');
    expect(assetGrid?.className).toContain('2xl:grid-cols-6');
    expect(assetGrid?.querySelectorAll('[role="listitem"]')).toHaveLength(1);
    expect(assetGrid?.querySelector('img')?.getAttribute('src')).toBe('/card-images/images/back.webp');
    mounted.unmount();
  });

  test('filters the library by its user-facing label rather than stored identifiers', async () => {
    mockLoads();
    const mounted = await mountView();
    const filterInput = mounted.container.querySelector<HTMLInputElement>('input[aria-label="Filter card backs"]');
    if (!filterInput) throw new Error('expected card-back filter');

    filterInput.value = 'back.png';
    filterInput.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    expect(mounted.container.querySelectorAll('[role="listitem"]')).toHaveLength(0);
    expect(mounted.container.textContent).toContain('No matching card backs');

    filterInput.value = 'default';
    filterInput.dispatchEvent(new Event('input', { bubbles: true }));
    await nextTick();
    expect(mounted.container.querySelectorAll('[role="listitem"]')).toHaveLength(1);
    mounted.unmount();
  });

  test('uploads an asset without changing a default', async () => {
    mockLoads([]);
    apiPost.mockResolvedValue({ data: buildCardBack({ label: 'Uploaded Back' }) });
    const mounted = await mountView();
    const openButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Add card back'),
    );
    if (!openButton) throw new Error('expected add card back action');
    openButton.click();
    await nextTick();
    const labelInput = document.body.querySelector<HTMLInputElement>('input[placeholder="Card back name"]');
    const fileInput = document.body.querySelector<HTMLInputElement>('input[type="file"]');
    const submitButton = Array.from(document.body.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Add to library'),
    );
    if (!labelInput || !fileInput || !submitButton) throw new Error('expected upload dialog controls');
    labelInput.value = 'Uploaded Back';
    labelInput.dispatchEvent(new Event('input', { bubbles: true }));
    Object.defineProperty(fileInput, 'files', {
      value: [new File(['image'], 'uploaded.png', { type: 'image/png' })],
      configurable: true,
    });
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();
    expect(document.body.querySelector('img[alt="Selected card back preview"]')?.getAttribute('src'))
      .toBe('blob:card-back-preview');
    submitButton.click();
    await flushPromises();
    expect(apiPost).toHaveBeenCalledWith('/admin/card-backs/upload', expect.any(FormData));
    expect(apiPut).not.toHaveBeenCalled();
    await vi.waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith('Card-back asset uploaded.');
    });
    mounted.unmount();
  });

  test('sets one pool default with the dedicated mutation', async () => {
    const second = buildCardBack({ id: 'card-back-2', label: 'Second Back', default_for_pools: [] });
    mockLoads([buildCardBack(), second]);
    apiPut.mockResolvedValue({ data: second });
    const mounted = await mountView();
    const playerSelect = mounted.container.querySelector<HTMLSelectElement>('select[aria-label="Player default card back"]');
    if (!playerSelect) throw new Error('expected Player default selector');
    playerSelect.value = second.id;
    playerSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/admin/card-backs/defaults/player', { card_back_id: second.id });
    mounted.unmount();
  });

  test('clears a pool default with the same authoritative mutation', async () => {
    mockLoads();
    apiPut.mockResolvedValue({ data: null });
    const mounted = await mountView();
    const playerSelect = mounted.container.querySelector<HTMLSelectElement>('select[aria-label="Player default card back"]');
    if (!playerSelect) throw new Error('expected Player default selector');
    playerSelect.value = '__placeholder__';
    playerSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/admin/card-backs/defaults/player', { card_back_id: null });
    mounted.unmount();
  });
});
