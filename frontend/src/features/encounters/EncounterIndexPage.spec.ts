import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import EncounterIndexPage from './EncounterIndexPage.vue';
import type { EncounterPage, EncounterSummary } from '@/domain/encounters/types';

const { fetchList, auth } = vi.hoisted(() => ({
  fetchList: vi.fn(),
  auth: { canAccessStaffRoutes: true, authenticated: true },
}));
vi.mock('@/domain/encounters/api', () => ({ fetchEncounters: fetchList }));
vi.mock('@/domain/session/store', () => ({ useAuthStore: () => auth }));
vi.mock('@/shared/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: { title: { type: String, required: true } },
    setup:
      (props, { slots }) =>
      () =>
        h('header', [props.title, slots.actions?.(), slots.center?.(), slots.bottomLeft?.()]),
  }),
}));
const record = (overrides: Partial<EncounterSummary> = {}): EncounterSummary => ({
  id: 'fight-1',
  is_official: false,
  can_edit: true,
  can_delete: true,
  name: 'Gate siege',
  description: 'Hold the gate against the invading army.',
  boss_card: null,
  boss_card_id: null,
  boss_group_id: null,
  factions: ['order'],
  visibility: 'public',
  creator: { id: 'another-staff', username: 'Another author' },
  total_cards: 23,
  sideboard_count: 0,
  revision: 1,
  status: { is_valid: true, issues: [] },
  created_at: '2026-10-01',
  updated_at: '2026-10-31',
  ...overrides,
});
const page = (results: EncounterSummary[], next: number | null = null): EncounterPage => ({
  count: results.length,
  next_page: next,
  results,
});
const cleanups: Array<() => void> = [];
const flush = async () => {
  await vi.advanceTimersByTimeAsync(0);
  await nextTick();
};
const mount = async (path = '/encounters') => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/encounters', component: EncounterIndexPage },
      { path: '/staff/encounters', component: EncounterIndexPage },
      { path: '/my/encounters', component: EncounterIndexPage },
      { path: '/my/encounters/:id/edit', component: { template: '<div />' } },
      { path: '/my/encounters/new', component: { template: '<div />' } },
      { path: '/encounters/:id', component: { template: '<div />' } },
    ],
  });
  await router.push(path);
  const target = document.createElement('div');
  document.body.appendChild(target);
  const app = createApp(EncounterIndexPage).use(router);
  app.mount(target);
  cleanups.push(() => {
    app.unmount();
    target.remove();
  });
  await flush();
  return { target, router };
};
beforeEach(() => {
  vi.useFakeTimers();
  fetchList.mockReset();
  auth.canAccessStaffRoutes = true;
  auth.authenticated = true;
});
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
  vi.useRealTimers();
});

test('public browsing uses summary cards and header filters without staff controls for anonymous visitors', async () => {
  auth.canAccessStaffRoutes = false;
  auth.authenticated = false;
  fetchList.mockResolvedValue(page([record({ can_edit: false, can_delete: false })]));
  const { target } = await mount();
  expect(fetchList.mock.calls[0][0]).toBe('public');
  expect(target.querySelector('.app-page-layout aside')).toBeNull();
  expect(target.querySelector('header [role="group"][aria-label="Factions"]')).not.toBeNull();
  expect(target.querySelector('.collection-list-card-surface')?.textContent).toContain(
    'Hold the gate',
  );
  expect(target.textContent).toContain('Another author');
  expect(target.querySelector('[aria-label="Edit Encounter"]')).toBeNull();
  expect(target.textContent).not.toContain('Staff Encounters');
});

test('staff mode displays other authors, private and unfinished records with edit links', async () => {
  fetchList.mockResolvedValue(
    page([
      record({
        name: '',
        visibility: 'private',
        total_cards: 0,
        sideboard_count: 0,
        status: { is_valid: false, issues: ['Choose a boss.'] },
      }),
    ]),
  );
  const { target, router } = await mount('/staff/encounters');
  expect(fetchList.mock.calls[0][0]).toBe('staff');
  expect(target.textContent).toContain('Untitled Encounter');
  expect(target.textContent).toContain('Private');
  expect(target.textContent).toContain('Under construction');
  expect(target.textContent).toContain('Another author');
  (target.querySelector('[aria-label="Edit Encounter"]') as HTMLElement).dispatchEvent(
    new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }),
  );
  await flush();
  expect(router.currentRoute.value.path).toBe('/my/encounters/fight-1/edit');
});

test('search and multiple faction filters survive the public/staff library switch and reset', async () => {
  fetchList.mockResolvedValue(page([]));
  const { target, router } = await mount('/encounters?q=gate&factions=order');
  Array.from(target.querySelectorAll('button'))
    .find((button) => button.textContent?.trim() === 'Fire')
    ?.click();
  await vi.advanceTimersByTimeAsync(300);
  await flush();
  expect(router.currentRoute.value.query.factions).toEqual(['order', 'fire']);
  const params = fetchList.mock.calls.at(-1)?.[1] as URLSearchParams;
  expect(params.get('q')).toBe('gate');
  expect(params.getAll('factions')).toEqual(['order', 'fire']);
  (target.querySelector('a[href^="/staff/encounters"]') as HTMLElement).dispatchEvent(
    new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }),
  );
  await flush();
  expect(router.currentRoute.value.query.q).toBe('gate');
  expect(fetchList.mock.calls.at(-1)?.[0]).toBe('staff');
  Array.from(target.querySelectorAll('button'))
    .find((button) => button.textContent?.trim() === 'Clear filters')
    ?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
  await vi.advanceTimersByTimeAsync(300);
  await flush();
  expect(router.currentRoute.value.query).toEqual({});
});

test('switching to public discards a late staff response', async () => {
  let resolveStaff!: (value: EncounterPage) => void;
  fetchList.mockImplementation((scope: string) =>
    scope === 'staff'
      ? new Promise<EncounterPage>((resolve) => {
          resolveStaff = resolve;
        })
      : Promise.resolve(page([record({ name: 'Public fight' })])),
  );
  const { target, router } = await mount('/staff/encounters');
  await router.push('/encounters');
  await flush();
  resolveStaff(page([record({ name: 'Private fight' })]));
  await flush();
  expect(target.textContent).toContain('Public fight');
  expect(target.textContent).not.toContain('Private fight');
});

test('pagination appends summaries, preserves existing cards after failure, and retries', async () => {
  fetchList
    .mockResolvedValueOnce(page([record()], 2))
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValueOnce(page([record(), record({ id: 'fight-2', name: 'Second fight' })]));
  const { target } = await mount();
  const button = () =>
    Array.from(target.querySelectorAll('button')).find((item) =>
      /Load more Encounters|Retry loading more/.test(item.textContent ?? ''),
    );
  button()?.click();
  await flush();
  expect(target.textContent).toContain('Gate siege');
  expect(target.textContent).toContain('Retry loading more');
  button()?.click();
  await flush();
  expect(target.querySelectorAll('.collection-list-card-surface')).toHaveLength(2);
  expect((fetchList.mock.calls.at(-1)?.[1] as URLSearchParams).get('page')).toBe('2');
});

test('initial errors offer retry and a successful empty response shows the empty state', async () => {
  fetchList.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(page([]));
  const { target } = await mount();
  expect(target.querySelector('[role="alert"]')).not.toBeNull();
  Array.from(target.querySelectorAll('button'))
    .find((button) => button.textContent?.trim() === 'Retry')
    ?.click();
  await flush();
  expect(target.textContent).toContain('No public Encounters yet.');
});

test('personal library preserves Official filters and shows read-only endorsed owner records', async () => {
  auth.canAccessStaffRoutes = false;
  fetchList.mockResolvedValue(
    page([
      record({ is_official: true, can_edit: false, can_delete: false, visibility: 'private' }),
    ]),
  );
  const { target, router } = await mount('/my/encounters?q=gate&factions=order&is_official=true');
  expect(fetchList.mock.calls[0][0]).toBe('mine');
  expect((fetchList.mock.calls[0][1] as URLSearchParams).get('is_official')).toBe('true');
  expect(target.querySelector('[aria-label="Encounter library"] [aria-current="page"]')?.textContent?.trim()).toBe(
    'Mine',
  );
  expect(target.querySelector('.collection-list-card-surface')?.textContent).toContain('Official');
  expect(target.querySelector('[aria-label="Edit Encounter"]')).toBeNull();
  const detail = target.querySelector('.collection-list-card-surface[role="link"]') as HTMLElement;
  detail.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
  await flush();
  expect(router.currentRoute.value.query).toMatchObject({
    return_to: 'my_encounters',
    is_official: 'true',
    q: 'gate',
    factions: ['order'],
  });
});

test('Official and Community filters compose with search and factions and clear back to All', async () => {
  fetchList.mockResolvedValue(page([]));
  const { target, router } = await mount('/encounters?q=gate&factions=fire');
  const select = (label: string) =>
    Array.from(target.querySelectorAll('button'))
      .find((button) => button.textContent?.trim() === label)
      ?.click();
  select('Community');
  await vi.advanceTimersByTimeAsync(300);
  await flush();
  expect(router.currentRoute.value.query).toMatchObject({
    is_official: 'false',
    q: 'gate',
    factions: ['fire'],
  });
  expect((fetchList.mock.calls.at(-1)?.[1] as URLSearchParams).get('is_official')).toBe('false');
  select('All');
  await vi.advanceTimersByTimeAsync(300);
  await flush();
  expect(router.currentRoute.value.query).not.toHaveProperty('is_official');
  expect(router.currentRoute.value.query.q).toBe('gate');
});
