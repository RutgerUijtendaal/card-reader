/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter, RouterLink } from 'vue-router';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import EncounterDetailPage from './EncounterDetailPage.vue';
import type { EncounterRecord } from '@/domain/encounters/types';
import type { CardListItem } from '@/domain/cards/types';

const { auth, fetchRecord, exportRecord, copyExport, fetchFilters } = vi.hoisted(() => ({
  auth: { canAccessStaffRoutes: true, authenticated: true, user: { id: 'owner' } },
  fetchRecord: vi.fn(),
  exportRecord: vi.fn(),
  copyExport: vi.fn(),
  fetchFilters: vi.fn(),
}));
vi.mock('@/domain/session/store', () => ({ useAuthStore: () => auth }));
vi.mock('@/domain/encounters/api', () => ({
  fetchEncounter: fetchRecord,
  exportEncounter: exportRecord,
  deleteEncounter: vi.fn(),
}));
vi.mock('@/domain/cards/api', () => ({ fetchCardFilters: fetchFilters }));
vi.mock('@/domain/cards/utils/copyTtsExport', () => ({ copyTtsExport: copyExport }));
vi.mock('@/domain/cards/utils/ttsExportResponse', () => ({
  ttsExportSheetDescription: () => 'One sheet.',
}));
vi.mock('@/shared/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    props: {
      title: { type: String, default: '' },
      backTo: { type: [String, Object], default: '' },
    },
    setup:
      (props, { slots }) =>
      () =>
        h('header', [
          h('h1', props.title),
          h(RouterLink, { to: props.backTo, 'data-testid': 'back' }),
          slots.subtitle?.(),
          slots.actions?.(),
          slots.bottomLeft?.(),
          slots.bottomRight?.(),
        ]),
  }),
}));
vi.mock('@/domain/cards/components/CardMarkupText.vue', () => ({
  default: defineComponent({
    props: { markup: { type: String, default: '' } },
    setup: (props) => () => h('p', props.markup),
  }),
}));
vi.mock('@/domain/cards/components/CardGalleryItem.vue', () => ({
  default: defineComponent({
    props: {
      card: { type: Object, required: true },
      navigationTarget: { type: Object, default: undefined },
    },
    setup:
      (props, { slots }) =>
      () =>
        h(
          'article',
          {
            'data-card-id': props.card.id,
            'data-navigation': JSON.stringify(props.navigationTarget),
          },
          [props.card.name, slots.overlay?.()],
        ),
  }),
}));
vi.mock('@/domain/cards/components/CardSortMenu.vue', () => ({
  default: { template: '<button>Sort</button>' },
}));
vi.mock('@/domain/cards/components/GalleryOptionsMenu.vue', () => ({
  default: defineComponent({
    props: { groupByType: Boolean },
    emits: ['update:groupByType'],
    setup:
      (props, { emit }) =>
      () =>
        h(
          'button',
          {
            'data-testid': 'group-toggle',
            onClick: () => emit('update:groupByType', !props.groupByType),
          },
          'Group by Type',
        ),
  }),
}));
const card = (id: string, role = '') =>
  ({
    id,
    name: id,
    card_pool: 'evil',
    card_factions: ['order'],
    card_roles: role ? [role] : [],
    card_mana_families: [],
    types: [],
    symbols: [],
    image_url: '/boss.png',
    mana_value: 0,
    result_type: 'card',
  }) as unknown as CardListItem;
const fixture = (override: Partial<EncounterRecord> = {}): EncounterRecord => ({
  id: 'fight-1',
  is_official: false,
  can_edit: true,
  can_delete: true,
  name: 'Gate siege',
  description: 'Hold the gate.',
  description_markup: 'Hold the gate.',
  long_description: 'Setup and tactics.',
  long_description_markup: 'Setup and tactics.',
  boss_card_id: 'boss',
  boss_group_id: 'group-1',
  boss_card: card('boss', 'boss'),
  sideboards: [],
  boss_cards: [card('boss', 'boss'), card('linked')],
  entries: [
    { card_id: 'army', card: card('army'), quantity: 19 },
    { card_id: 'boss', card: card('boss', 'boss'), quantity: 2 },
  ],
  factions: ['order'],
  total_cards: 21,
  sideboard_count: 0,
  visibility: 'public',
  revision: 1,
  creator: { id: 'staff-2', username: 'Another author' },
  status: { is_valid: true, issues: [] },
  created_at: '2026-10-31',
  updated_at: '2026-10-31',
  ...override,
});
const cleanups: Array<() => void> = [];
const flush = async () => {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await nextTick();
};
const mount = async (path = '/encounters/fight-1') => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/encounters/:id', component: EncounterDetailPage },
      { path: '/my/encounters/:id/edit', component: { template: '<div />' } },
      { path: '/staff/encounters', component: { template: '<div />' } },
      { path: '/encounters', component: { template: '<div />' } },
    ],
  });
  await router.push(path);
  const target = document.createElement('div');
  document.body.appendChild(target);
  const app = createApp(EncounterDetailPage).use(router);
  app.mount(target);
  cleanups.push(() => {
    app.unmount();
    target.remove();
  });
  await flush();
  return { target, router };
};
const click = async (target: HTMLElement, text: string) => {
  const button = Array.from(target.querySelectorAll('button')).find((item) =>
    item.textContent?.trim().startsWith(text),
  );
  expect(button).toBeDefined();
  button?.click();
  await flush();
};
beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  auth.canAccessStaffRoutes = true;
  fetchRecord.mockResolvedValue(fixture());
  fetchFilters.mockResolvedValue({ types: [], symbols: [], tags: [], keywords: [] });
  exportRecord.mockResolvedValue({ encodedPayload: 'tts-code', exportedCount: 23 });
  copyExport.mockResolvedValue(undefined);
});
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
});

test('uses the shared detail layout with boss information left and quantity galleries right', async () => {
  const { target } = await mount('/encounters/fight-1?return_to=encounters');
  expect(fetchRecord).toHaveBeenCalledWith('fight-1', false);
  expect(fetchFilters).toHaveBeenCalledWith('evil');
  expect(target.querySelector('.collection-detail-primary-aside')?.textContent).toContain(
    'Another author',
  );
  expect(target.querySelector('.collection-detail-primary-aside')?.textContent).toContain(
    'Hold the gate.',
  );
  expect(
    target.querySelector('.app-page-layout-main [data-card-id="army"]')?.textContent,
  ).toContain('x19');
  expect(
    target.querySelector('.app-page-layout-main [data-card-id="boss"]')?.textContent,
  ).toContain('x2');
  expect(target.querySelector('[data-testid="back"]')?.getAttribute('href')).toBe('/encounters');
  expect(target.querySelector('[data-card-id="army"]')?.getAttribute('data-navigation')).toContain(
    'encounter_library',
  );
});

test('boss view includes linked cards once and preserves separate mainboard quantities', async () => {
  const { target } = await mount();
  await click(target, 'Boss');
  expect(target.querySelectorAll('article')).toHaveLength(2);
  expect(target.querySelector('[data-card-id="boss"]')?.textContent).toContain('x1');
  expect(target.querySelector('[data-card-id="linked"]')).not.toBeNull();
  await click(target, 'Mainboard');
  expect(target.querySelector('[data-card-id="boss"]')?.textContent).toContain('x2');
  expect(target.querySelector('[data-card-id="linked"]')).toBeNull();
});

test('long descriptions expand beside the summary and grouping remains a display preference', async () => {
  const { target } = await mount();
  await click(target, 'Details');
  expect(target.querySelector('.collection-detail-layout-expanded')).not.toBeNull();
  expect(target.querySelector('[data-testid="encounter-long-description"]')?.textContent).toContain(
    'Setup and tactics.',
  );
  await click(target, 'Close details');
  expect(target.querySelector('.collection-detail-layout-expanded')).toBeNull();
  expect(target.querySelector('[data-testid="card-type-group"]')).not.toBeNull();
  await click(target, 'Group by Type');
  expect(target.querySelector('[data-testid="card-type-group"]')).toBeNull();
  expect(localStorage.getItem('card-reader.encounter-detail-group-by-type')).toBe('false');
});

test('incomplete staff records show actionable issues without requiring a boss or entries', async () => {
  fetchRecord.mockResolvedValue(
    fixture({
      name: '',
      boss_card: null,
      boss_cards: [],
      entries: [],
      total_cards: 0,
      sideboard_count: 0,
      visibility: 'private',
      status: { is_valid: false, issues: ['Choose a boss.', 'Add at least 20 cards.'] },
    }),
  );
  const { target } = await mount();
  expect(target.textContent).toContain('No boss selected');
  expect(target.textContent).toContain('Private');
  expect(target.textContent).toContain('Choose a boss.');
  expect(target.textContent).toContain('No cards added to this Encounter yet.');
  expect(target.querySelector('a[aria-label="Edit Encounter"]')).not.toBeNull();
});

test('anonymous detail uses the public API, hides staff actions, and exports the full Encounter from either view', async () => {
  auth.canAccessStaffRoutes = false;
  fetchRecord.mockResolvedValue(fixture({ can_edit: false, can_delete: false }));
  const { target } = await mount();
  expect(fetchRecord).toHaveBeenCalledWith('fight-1', false);
  expect(target.querySelector('a[aria-label="Edit Encounter"]')).toBeNull();
  expect(target.querySelector('[aria-label="More Encounter actions"]')).toBeNull();
  await click(target, 'Boss');
  (target.querySelector('[aria-label="Copy Encounter TTS"]') as HTMLElement).click();
  await flush();
  expect(exportRecord).toHaveBeenCalledWith('fight-1', undefined);
  expect(copyExport).toHaveBeenCalled();
  expect(target.querySelector('textarea')?.value).toBe('tts-code');
});

test('official owners see a read-only explanation and return to their filtered personal library', async () => {
  auth.canAccessStaffRoutes = false;
  fetchRecord.mockResolvedValue(
    fixture({
      is_official: true,
      can_edit: false,
      can_delete: false,
      creator: { id: 'owner', username: 'Owner' },
    }),
  );
  const { target } = await mount(
    '/encounters/fight-1?return_to=my_encounters&is_official=true&q=gate',
  );
  expect(target.textContent).toContain('Only staff can edit or delete it.');
  expect(target.querySelector('a[aria-label="Edit Encounter"]')).toBeNull();
  expect(target.querySelector('[aria-label="More Encounter actions"]')).toBeNull();
  expect(target.querySelector('[data-testid="back"]')?.getAttribute('href')).toContain(
    '/my/encounters?q=gate&is_official=true',
  );
});

test('loading uses the shared page skeleton and late responses cannot replace the current Encounter', async () => {
  let resolveFirst!: (record: EncounterRecord) => void;
  fetchRecord.mockImplementation((id: string) =>
    id === 'fight-1'
      ? new Promise<EncounterRecord>((resolve) => {
          resolveFirst = resolve;
        })
      : Promise.resolve(fixture({ id, name: 'Second fight' })),
  );
  const { target, router } = await mount();
  expect(target.querySelector('[aria-label="Loading encounter detail"]')).not.toBeNull();
  await router.push('/encounters/fight-2');
  await flush();
  resolveFirst(fixture());
  await flush();
  expect(target.querySelector('h1')?.textContent).toBe('Second fight');
});

test('unavailable encounters show the API failure without cards or export actions', async () => {
  fetchRecord.mockRejectedValueOnce(new Error('unavailable'));
  const { target } = await mount();
  expect(target.querySelector('[role="alert"]')?.textContent).toContain(
    'Encounter not found or unavailable',
  );
  expect(target.querySelectorAll('article')).toHaveLength(0);
  expect(target.querySelector('[aria-label="Copy Encounter TTS"]')).toBeNull();
});

test('sideboard tabs show saved quantities and export only the selected board', async () => {
  const base = fixture();
  fetchRecord.mockResolvedValue(
    fixture({
      sideboards: [{ id: 'reserve', name: 'Reinforcements', entries: [base.entries[0]] }],
    }),
  );
  const { target } = await mount();
  await click(target, 'Reinforcements');
  (target.querySelector('[aria-label="Copy Sideboard TTS"]') as HTMLElement).click();
  await flush();
  expect(exportRecord).toHaveBeenCalledWith('fight-1', 'reserve');
  await click(target, 'Mainboard');
  expect(target.querySelector('[aria-label="Copy Encounter TTS"]')).not.toBeNull();
});
