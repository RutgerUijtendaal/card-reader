import { createApp, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
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
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] });
  app.use(router);
  await router.push('/admin');
  await router.isReady();
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

  test('opens the dedicated import flow without mutating defaults', async () => {
    mockLoads([]);
    const mounted = await mountView();
    await openLibrary(mounted.container);
    expect(mounted.container.querySelector('a[href="/admin/card-backs/import"]')?.textContent).toContain('Import card backs');
    expect(apiPut).not.toHaveBeenCalled();
    mounted.unmount();
  });

  test('combines usage filters with label search', async () => {
    mockLoads([
      buildCardBack({ id: 'both', label: 'Hero shared' }),
      buildCardBack({ id: 'unused', label: 'Hero unused', default_for_pools: [], override_card_count: 0 }),
      buildCardBack({ id: 'default', label: 'General', override_card_count: 0 }),
    ]);
    const mounted = await mountView();
    await openLibrary(mounted.container);
    const usage = mounted.container.querySelector<HTMLSelectElement>('select[aria-label="Card-back usage"]')!;
    usage.value = 'unused';
    usage.dispatchEvent(new Event('change'));
    await nextTick();
    expect(mounted.container.querySelector('[role="list"]')?.textContent).toContain('Hero unused');
    expect(mounted.container.querySelector('[role="list"]')?.textContent).not.toContain('Hero shared');
    usage.value = 'defaults';
    usage.dispatchEvent(new Event('change'));
    const search = mounted.container.querySelector<HTMLInputElement>('input[aria-label="Filter card backs"]')!;
    search.value = 'Hero';
    search.dispatchEvent(new Event('input'));
    await nextTick();
    expect(mounted.container.querySelector('[role="list"]')?.textContent).toContain('Hero shared');
    expect(mounted.container.querySelector('[role="list"]')?.textContent).not.toContain('General');
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
