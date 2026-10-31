import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import EncounterIndexPage from './EncounterIndexPage.vue';
import type { EncounterPage, EncounterSummary } from '@/domain/encounters/types';

const { fetchList, auth } = vi.hoisted(() => ({
  fetchList: vi.fn(),
  auth: { canAccessStaffRoutes: true },
}));
vi.mock('@/domain/encounters/api', () => ({ fetchEncounters: fetchList }));
vi.mock('@/domain/session/store', () => ({ useAuthStore: () => auth }));
vi.mock('@/shared/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: { title: { type: String, required: true } },
    setup:
      (props, { slots }) =>
      () =>
        h('header', [props.title, slots.actions?.()]),
  }),
}));
const record = (overrides: Partial<EncounterSummary> = {}): EncounterSummary => ({
  id: 'fight-1',
  name: 'Gate siege',
  description: 'Hold the gate against the invading army.',
  boss_card: null,
  boss_card_id: null,
  boss_group_id: null,
  factions: ['order'],
  visibility: 'public',
  creator: { id: 'another-staff', username: 'Another author' },
  total_cards: 23,
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
      { path: '/staff/encounters/:id/edit', component: { template: '<div />' } },
      { path: '/staff/encounters/new', component: { template: '<div />' } },
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
});
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
  vi.useRealTimers();
});

test('public browsing uses summary cards and a left sidebar without staff controls for anonymous visitors', async () => {
  auth.canAccessStaffRoutes = false;
  fetchList.mockResolvedValue(page([record()]));
  const { target } = await mount();
  expect(fetchList.mock.calls[0][0]).toBe(false);
  expect(target.querySelector('.app-page-layout')?.firstElementChild?.tagName).toBe('ASIDE');
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
        status: { is_valid: false, issues: ['Choose a boss.'] },
      }),
    ]),
  );
  const { target, router } = await mount('/staff/encounters');
  expect(fetchList.mock.calls[0][0]).toBe(true);
  expect(target.textContent).toContain('Untitled Encounter');
  expect(target.textContent).toContain('Staff only');
  expect(target.textContent).toContain('Under construction');
  expect(target.textContent).toContain('Another author');
  (target.querySelector('[aria-label="Edit Encounter"]') as HTMLElement).dispatchEvent(
    new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }),
  );
  await flush();
  expect(router.currentRoute.value.path).toBe('/staff/encounters/fight-1/edit');
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
  (
    target.querySelector('.theme-tablist a[href^="/staff/encounters"]') as HTMLElement
  ).dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }));
  await flush();
  expect(router.currentRoute.value.query.q).toBe('gate');
  expect(fetchList.mock.calls.at(-1)?.[0]).toBe(true);
  (target.querySelector('[aria-label="Reset filters"]') as HTMLElement).dispatchEvent(
    new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 }),
  );
  await vi.advanceTimersByTimeAsync(300);
  await flush();
  expect(router.currentRoute.value.query).toEqual({});
});

test('switching to public discards a late staff response', async () => {
  let resolveStaff!: (value: EncounterPage) => void;
  fetchList.mockImplementation((staff: boolean) =>
    staff
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
