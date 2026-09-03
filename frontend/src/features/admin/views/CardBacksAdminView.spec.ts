import { createApp, nextTick } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import CardBacksAdminView from '@/features/admin/views/CardBacksAdminView.vue';
import type {
  CardBackFactionDefaults,
  CardBackRecord,
  CardBackRoleDefaults,
} from '@/domain/card-backs/types';

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
  default_for_factions: [],
  default_for_roles: [],
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

const deferred = <T>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
};

const emptyFactionDefaults = (): CardBackFactionDefaults => ({
  order: null,
  blood: null,
  dark: null,
  metal: null,
  fire: null,
});

const emptyRoleDefaults = (): CardBackRoleDefaults => ({
  hero: null,
  boss: null,
  location: null,
  boon: null,
  event: null,
  shop_item: null,
  directive: null,
  reminder: null,
  mana: null,
});

const mountView = async () => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp(CardBacksAdminView);
  app.mount(container);
  await flushPromises();
  await nextTick();
  return { container, unmount: () => { app.unmount(); container.remove(); } };
};

const openLibrary = async (container: HTMLElement): Promise<void> => {
  const libraryButton = Array.from(container.querySelectorAll<HTMLButtonElement>('button')).find((button) =>
    button.textContent?.includes('Library'),
  );
  if (!libraryButton) throw new Error('expected Library view action');
  libraryButton.click();
  await nextTick();
};

const mockLoads = (assets = [buildCardBack()]): void => {
  apiGet.mockImplementation((url: string) => Promise.resolve({
    data: url === '/card-backs/defaults'
      ? { player: assets[0] ?? null, evil: null, neutral: null }
      : url === '/card-backs/role-defaults'
        ? emptyRoleDefaults()
      : url === '/card-backs/faction-defaults'
        ? emptyFactionDefaults()
      : assets,
  }));
};

describe('CardBacksAdminView', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  test('separates compact defaults from the reusable asset library', async () => {
    mockLoads();
    const mounted = await mountView();
    expect(apiGet).toHaveBeenCalledWith('/admin/card-backs');
    expect(apiGet).toHaveBeenCalledWith('/card-backs/defaults');
    expect(apiGet).toHaveBeenCalledWith('/card-backs/faction-defaults');
    expect(apiGet).toHaveBeenCalledWith('/card-backs/role-defaults');
    expect(mounted.container.textContent).toContain('Role defaults');
    expect(mounted.container.textContent).toContain('Evil faction defaults');
    expect(mounted.container.textContent).toContain('Pool defaults');
    expect(mounted.container.textContent).toContain('Resolution order');
    expect(mounted.container.textContent).toContain('0 of 9 configured');
    expect(mounted.container.textContent).toContain('0 of 5 configured');
    expect(mounted.container.textContent).toContain('1 of 3 configured');
    expect(mounted.container.querySelector('select[aria-label="Normal role default card back"]')).toBeNull();
    expect(mounted.container.querySelector('[role="list"][aria-label="Card-back assets"]')).toBeNull();

    await openLibrary(mounted.container);
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
    await openLibrary(mounted.container);
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
    await openLibrary(mounted.container);
    const openButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Add card back'),
    );
    if (!openButton) throw new Error('expected add card back action');
    openButton.click();
    await nextTick();
    const dialogPanel = document.body.querySelector('[role="dialog"] > div');
    expect(dialogPanel?.className).toContain('app-scrollbar');
    expect(dialogPanel?.className).toContain('max-h-[90vh]');
    expect(dialogPanel?.className).toContain('overflow-y-auto');
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

  test('locks every editable upload field to its submitted payload', async () => {
    mockLoads([]);
    let resolveUpload: ((value: unknown) => void) | undefined;
    apiPost.mockImplementation(() => new Promise((resolve) => {
      resolveUpload = resolve;
    }));
    const mounted = await mountView();
    await openLibrary(mounted.container);
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
    Object.defineProperty(fileInput, 'files', {
      value: [new File(['image'], 'uploaded.png', { type: 'image/png' })],
      configurable: true,
    });
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();
    submitButton.click();
    await nextTick();
    expect(labelInput.disabled).toBe(true);

    resolveUpload?.({ data: buildCardBack() });
    await flushPromises();
    mounted.unmount();
  });

  test('releases the upload lock before the library refresh settles', async () => {
    mockLoads([]);
    apiPost.mockResolvedValue({ data: buildCardBack() });
    const mounted = await mountView();
    await openLibrary(mounted.container);
    apiGet.mockImplementation(() => new Promise(() => {}));
    const openButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Add card back'),
    );
    if (!openButton) throw new Error('expected add card back action');
    openButton.click();
    await nextTick();
    const fileInput = document.body.querySelector<HTMLInputElement>('input[type="file"]');
    const submitButton = Array.from(document.body.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Add to library'),
    );
    if (!fileInput || !submitButton) throw new Error('expected upload dialog controls');
    Object.defineProperty(fileInput, 'files', {
      value: [new File(['image'], 'uploaded.png', { type: 'image/png' })],
      configurable: true,
    });
    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();
    submitButton.click();
    await flushPromises();

    openButton.click();
    await nextTick();
    const reopenedLabel = document.body.querySelector<HTMLInputElement>('input[placeholder="Card back name"]');
    const closeButton = document.body.querySelector<HTMLButtonElement>('button[aria-label="Close add card back dialog"]');
    expect(reopenedLabel?.disabled).toBe(false);
    expect(closeButton?.disabled).toBe(false);
    closeButton?.click();
    await nextTick();
    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
    mounted.unmount();
  });

  test('ignores an older post-upload refresh that finishes after a newer one', async () => {
    mockLoads([]);
    apiPost.mockResolvedValue({ data: buildCardBack() });
    const mounted = await mountView();
    await openLibrary(mounted.container);
    const firstAssets = deferred<{ data: CardBackRecord[] }>();
    const firstDefaults = deferred<{ data: { player: CardBackRecord; evil: null; neutral: null } }>();
    const secondAssets = deferred<{ data: CardBackRecord[] }>();
    const secondDefaults = deferred<{ data: { player: CardBackRecord; evil: null; neutral: null } }>();
    let assetRequestCount = 0;
    let defaultsRequestCount = 0;
    apiGet.mockImplementation((url: string) => {
      if (url === '/card-backs/defaults') {
        defaultsRequestCount += 1;
        return defaultsRequestCount === 1 ? firstDefaults.promise : secondDefaults.promise;
      }
      if (url === '/card-backs/faction-defaults') {
        return Promise.resolve({ data: emptyFactionDefaults() });
      }
      if (url === '/card-backs/role-defaults') {
        return Promise.resolve({ data: emptyRoleDefaults() });
      }
      assetRequestCount += 1;
      return assetRequestCount === 1 ? firstAssets.promise : secondAssets.promise;
    });

    const submitUpload = async (filename: string): Promise<void> => {
      const openButton = Array.from(mounted.container.querySelectorAll('button')).find((button) =>
        button.textContent?.includes('Add card back'),
      );
      if (!openButton) throw new Error('expected add card back action');
      openButton.click();
      await nextTick();
      const fileInput = document.body.querySelector<HTMLInputElement>('input[type="file"]');
      const submitButton = Array.from(document.body.querySelectorAll('button')).find((button) =>
        button.textContent?.includes('Add to library'),
      );
      if (!fileInput || !submitButton) throw new Error('expected upload dialog controls');
      Object.defineProperty(fileInput, 'files', {
        value: [new File(['image'], filename, { type: 'image/png' })],
        configurable: true,
      });
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
      await nextTick();
      submitButton.click();
      await flushPromises();
    };

    await submitUpload('first.png');
    await submitUpload('second.png');
    const newer = buildCardBack({ id: 'newer', label: 'Newer Back' });
    secondAssets.resolve({ data: [newer] });
    secondDefaults.resolve({ data: { player: newer, evil: null, neutral: null } });
    await flushPromises();
    await nextTick();
    expect(mounted.container.textContent).toContain('Newer Back');

    const older = buildCardBack({ id: 'older', label: 'Older Back' });
    firstAssets.resolve({ data: [older] });
    firstDefaults.resolve({ data: { player: older, evil: null, neutral: null } });
    await flushPromises();
    await nextTick();
    expect(mounted.container.textContent).toContain('Newer Back');
    expect(mounted.container.textContent).not.toContain('Older Back');
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

  test('sets an Evil faction default with the dedicated mutation', async () => {
    const second = buildCardBack({ id: 'card-back-2', label: 'Second Back', default_for_pools: [] });
    mockLoads([buildCardBack(), second]);
    apiPut.mockResolvedValue({ data: second });
    const mounted = await mountView();
    const orderSelect = mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Order faction default card back"]',
    );
    if (!orderSelect) throw new Error('expected Order faction default selector');

    orderSelect.value = second.id;
    orderSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/admin/card-backs/faction-defaults/order', {
      card_back_id: second.id,
    });
    mounted.unmount();
  });

  test('sets a role default with the dedicated mutation', async () => {
    const second = buildCardBack({ id: 'card-back-2', label: 'Second Back', default_for_pools: [] });
    mockLoads([buildCardBack(), second]);
    apiPut.mockResolvedValue({ data: second });
    const mounted = await mountView();
    const heroSelect = mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Hero role default card back"]',
    );
    if (!heroSelect) throw new Error('expected Hero role default selector');

    heroSelect.value = second.id;
    heroSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/admin/card-backs/role-defaults/hero', {
      card_back_id: second.id,
    });
    mounted.unmount();
  });

  test('locks every default section while a role mutation is pending', async () => {
    const second = buildCardBack({ id: 'card-back-2', label: 'Second Back', default_for_pools: [] });
    mockLoads([buildCardBack(), second]);
    const pendingMutation = deferred<{ data: CardBackRecord }>();
    apiPut.mockReturnValue(pendingMutation.promise);
    const mounted = await mountView();
    const heroSelect = mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Hero role default card back"]',
    );
    if (!heroSelect) throw new Error('expected Hero role default selector');

    heroSelect.value = second.id;
    heroSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();

    expect(mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Player default card back"]',
    )?.disabled).toBe(true);
    expect(mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Boss role default card back"]',
    )?.disabled).toBe(true);
    expect(mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Order faction default card back"]',
    )?.disabled).toBe(true);

    pendingMutation.resolve({ data: second });
    await flushPromises();
    mounted.unmount();
  });

  test('clears a role default and shows that unset defaults continue down the hierarchy', async () => {
    const selected = buildCardBack({ default_for_pools: [], default_for_roles: ['hero'] });
    let roleDefaultsRequestCount = 0;
    apiGet.mockImplementation((url: string) => Promise.resolve({
      data: url === '/card-backs/defaults'
        ? { player: null, evil: null, neutral: null }
        : url === '/card-backs/role-defaults'
          ? (++roleDefaultsRequestCount === 1
              ? { ...emptyRoleDefaults(), hero: selected }
              : emptyRoleDefaults())
          : url === '/card-backs/faction-defaults'
            ? emptyFactionDefaults()
            : [selected],
    }));
    apiPut.mockResolvedValue({ data: null });
    const mounted = await mountView();
    const heroSelect = mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Hero role default card back"]',
    );
    if (!heroSelect) throw new Error('expected Hero role default selector');

    heroSelect.value = '__placeholder__';
    heroSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/admin/card-backs/role-defaults/hero', {
      card_back_id: null,
    });
    expect(mounted.container.textContent).toContain('Unset defaults continue to the next level.');
    await vi.waitFor(() => {
      expect(mounted.container.textContent).toContain('0 of 9 configured');
      expect(heroSelect.closest('article')?.textContent).toContain('Not set');
    });
    mounted.unmount();
  });

  test('clears an Evil faction default with the same authoritative mutation', async () => {
    const selected = buildCardBack({ default_for_pools: [], default_for_factions: ['order'] });
    apiGet.mockImplementation((url: string) => Promise.resolve({
      data: url === '/card-backs/defaults'
        ? { player: null, evil: null, neutral: null }
        : url === '/card-backs/role-defaults'
          ? emptyRoleDefaults()
        : url === '/card-backs/faction-defaults'
          ? { ...emptyFactionDefaults(), order: selected }
          : [selected],
    }));
    apiPut.mockResolvedValue({ data: null });
    const mounted = await mountView();
    const orderSelect = mounted.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Order faction default card back"]',
    );
    if (!orderSelect) throw new Error('expected Order faction default selector');

    orderSelect.value = '__placeholder__';
    orderSelect.dispatchEvent(new Event('change', { bubbles: true }));
    await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/admin/card-backs/faction-defaults/order', {
      card_back_id: null,
    });
    mounted.unmount();
  });
});
