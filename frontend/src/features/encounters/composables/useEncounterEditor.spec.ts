/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import type { CardListItem, GalleryItem } from '@/domain/cards/types';
import { emptyEncounter, type EncounterRecord } from '@/domain/encounters/types';
import { buildEncounterDraft, encounterDraftKey } from '../utils/draftStorage';
import { useEncounterEditor } from './useEncounterEditor';

const mocks = vi.hoisted(() => ({
  auth: { user: { id: 'staff' }, canAccessStaffRoutes: false },
  create: vi.fn(),
  lookup: vi.fn(),
  fetch: vi.fn(),
  update: vi.fn(),
  card: vi.fn(),
}));
vi.mock('@/domain/session/store', () => ({ useAuthStore: () => mocks.auth }));
vi.mock('@/domain/cards/api', () => ({ fetchCard: mocks.card }));
vi.mock('@/domain/encounters/api', () => ({
  createEncounter: mocks.create,
  lookupEncounterCreation: mocks.lookup,
  fetchEncounter: mocks.fetch,
  updateEncounter: mocks.update,
  fetchEncounterRules: async () => ({ minimum_cards: 20 }),
}));
vi.mock('vue-sonner', () => ({ toast: { error: vi.fn(), info: vi.fn(), success: vi.fn() } }));
const card = (id: string, factions: CardListItem['card_factions'] = []): CardListItem => ({
  id,
  result_type: 'card',
  card_pool: 'evil',
  card_roles: [],
  card_factions: factions,
  name: id,
  key: id,
  label: id,
  template_id: '',
  version_id: `${id}-v1`,
  version_number: 1,
  previous_version_id: null,
  is_latest: true,
  type_line: '',
  mana_cost: '',
  mana_symbols: [],
  mana_value: 0,
  attack: null,
  health: null,
  rules_text: '',
  confidence: 1,
  created_at: '',
  updated_at: '',
  keywords: [],
  tags: [],
  symbols: [],
  types: [],
  image_url: null,
});
const saved = (): EncounterRecord => ({
  ...emptyEncounter(),
  id: 'saved',
  is_official: false,
  can_edit: true,
  can_delete: true,
  revision: 1,
  description: '',
  long_description: '',
  boss_card: null,
  boss_cards: [],
  sideboards: [],
  entries: [],
  total_cards: 0,
  sideboard_count: 0,
  status: { is_valid: false, issues: ['Select a boss.'] },
  creator: { id: 'staff', username: 'Staff' },
  created_at: '',
  updated_at: '',
});
const cleanup: Array<() => void> = [];
const flush = async () => {
  await nextTick();
  await vi.advanceTimersByTimeAsync(0);
  await nextTick();
};
const mount = async (path = '/my/encounters/new') => {
  let editor!: ReturnType<typeof useEncounterEditor>;
  const view = defineComponent({
    setup() {
      editor = useEncounterEditor();
      return () => h('div');
    },
  });
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/my/encounters/new', component: view },
      { path: '/my/encounters/:id/edit', component: { template: '<div />' } },
      { path: '/my/encounters', component: { template: '<div />' } },
      { path: '/encounters/:id', component: { template: '<div />' } },
      { path: '/existing/:id', component: view },
    ],
  });
  await router.push(path);
  const container = document.createElement('div');
  document.body.appendChild(container);
  const app = createApp({ template: '<RouterView />' });
  app.use(router);
  app.mount(container);
  cleanup.push(() => {
    app.unmount();
    container.remove();
  });
  await flush();
  return { editor, router };
};
beforeEach(() => {
  mocks.auth.canAccessStaffRoutes = false;
  vi.useFakeTimers();
  vi.clearAllMocks();
  localStorage.clear();
  Object.defineProperty(navigator, 'locks', {
    configurable: true,
    value: {
      request: async (_name: string, _options: unknown, callback: () => unknown) => callback(),
    },
  });
  mocks.card.mockImplementation(async (id: string) => card(id, ['order', 'blood']));
  mocks.fetch.mockResolvedValue(saved());
  mocks.create.mockResolvedValue({ record: saved() });
  mocks.lookup.mockResolvedValue({ status: 'found', record: saved() });
});
afterEach(() => {
  cleanup.splice(0).forEach((fn) => fn());
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('Encounter authoring with shared draft machinery', () => {
  test('cards-first drafts retain quantities, order, markup and independent faction tags after refresh', async () => {
    const { editor } = await mount();
    editor.add(card('a'));
    editor.add(card('b'));
    editor.quantity('a', 19);
    editor.move(1, -1);
    editor.form.description_markup = 'Opening instructions';
    editor.form.factions = ['fire'];
    await vi.advanceTimersByTimeAsync(450);
    cleanup.splice(0).forEach((fn) => fn());
    const recovered = (await mount()).editor;
    expect(recovered.draft.pendingRecovery.value).not.toBeNull();
    await recovered.recover(recovered.draft.pendingRecovery.value!);
    expect(recovered.form.entries).toEqual([
      { card_id: 'b', quantity: 1 },
      { card_id: 'a', quantity: 19 },
    ]);
    expect(recovered.form.description_markup).toBe('Opening instructions');
    expect(recovered.form.factions).toEqual(['fire']);
    expect(recovered.form.boss_card_id).toBeNull();
    expect(recovered.total.value).toBe(20);
  });
  test.each(['details', 'boss'] as const)(
    '%s-first work can be explicitly created while incomplete',
    async (first) => {
      const { editor, router } = await mount();
      if (first === 'details') editor.form.name = 'Draft';
      else await editor.selectBoss(card('boss'));
      await editor.save();
      expect(mocks.create).toHaveBeenCalledTimes(1);
      expect(router.currentRoute.value.path).toBe('/my/encounters/saved/edit');
    },
  );
  test('boss presets include all factions while boss changes preserve cards and assigned tags', async () => {
    const { editor } = await mount();
    editor.add(card('a'));
    editor.form.factions = ['metal'];
    await editor.selectBoss({
      result_type: 'card_group',
      anchor_card_id: 'boss',
      group_id: 'pair',
    } as GalleryItem);
    expect(editor.factions.value).toEqual(['order', 'blood']);
    expect(editor.form.boss_group_id).toBe('pair');
    editor.factions.value = ['dark'];
    await editor.selectBoss(card('next'));
    expect(editor.factions.value).toEqual(['order', 'blood']);
    await editor.selectBoss(null);
    expect(editor.factions.value).toEqual([]);
    expect(editor.form.factions).toEqual(['metal']);
    expect(editor.form.entries).toEqual([{ card_id: 'a', quantity: 1 }]);
    editor.add({ ...card('player'), card_pool: 'player' });
    expect(editor.form.entries).toHaveLength(1);
  });
  test('stale server edits preserve the local form and stop autosync', async () => {
    const { editor } = await mount('/existing/saved');
    editor.form.name = 'My edits';
    editor.autosync.value = true;
    mocks.update.mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: { detail: 'Changed by another staff member.' } },
    });
    await editor.save();
    expect(editor.serverConflict.value).toBe(true);
    expect(editor.form.name).toBe('My edits');
    expect(editor.autosync.value).toBe(false);
    expect(mocks.update).toHaveBeenCalledWith(
      'saved',
      expect.objectContaining({ name: 'My edits' }),
      1,
    );
  });
  test('recovering an uncertain create reconciles before card hydration and never creates again', async () => {
    const form = emptyEncounter();
    form.entries = [{ card_id: 'a', quantity: 1 }];
    const attempt = { payload: form, signature: JSON.stringify(form), startedAt: '2026-10-31' };
    const stored = buildEncounterDraft(
      'staff',
      crypto.randomUUID(),
      form,
      { a: card('a') },
      attempt,
    );
    localStorage.setItem(encounterDraftKey('staff'), JSON.stringify(stored));
    const { editor, router } = await mount();
    mocks.card.mockRejectedValue(new Error('offline'));
    await editor.recover(editor.draft.pendingRecovery.value!);
    expect(router.currentRoute.value.path).toBe('/my/encounters/saved/edit');
    expect(mocks.create).not.toHaveBeenCalled();
  });
  test('a deleted create receipt navigates away without recreating the deleted Encounter', async () => {
    const form = emptyEncounter();
    form.name = 'Deleted draft';
    const stored = buildEncounterDraft(
      'staff',
      crypto.randomUUID(),
      form,
      {},
      { payload: form, signature: JSON.stringify(form), startedAt: 'now' },
    );
    localStorage.setItem(encounterDraftKey('staff'), JSON.stringify(stored));
    mocks.lookup.mockResolvedValue({ status: 'deleted' });
    const { editor, router } = await mount();
    await editor.recover(editor.draft.pendingRecovery.value!);
    expect(router.currentRoute.value.path).toBe('/my/encounters');
    expect(mocks.create).not.toHaveBeenCalled();
  });
  test('another tab creates a recoverable conflict instead of overwriting local work', async () => {
    const { editor } = await mount();
    editor.form.name = 'This tab';
    await editor.draft.persist();
    const other = buildEncounterDraft(
      'staff',
      crypto.randomUUID(),
      { ...emptyEncounter(), name: 'Other tab' },
      {},
      null,
    );
    const raw = JSON.stringify(other);
    localStorage.setItem(encounterDraftKey('staff'), raw);
    window.dispatchEvent(
      new StorageEvent('storage', { key: encounterDraftKey('staff'), newValue: raw }),
    );
    expect(editor.locked.value).toBe(true);
    await editor.save();
    expect(mocks.create).not.toHaveBeenCalled();
    await editor.loadConflict();
    expect(editor.form.name).toBe('Other tab');
  });
  test('a conflict during recovery keeps the recovered contents as the local candidate', async () => {
    const original = buildEncounterDraft(
      'staff',
      crypto.randomUUID(),
      {
        ...emptyEncounter(),
        name: 'Recovered work',
        factions: ['fire'],
        entries: [{ card_id: 'a', quantity: 20 }],
      },
      { a: card('a') },
      null,
    );
    localStorage.setItem(encounterDraftKey('staff'), JSON.stringify(original));
    const { editor } = await mount();
    expect(editor.draft.pendingRecovery.value).not.toBeNull();
    const remote = buildEncounterDraft(
      'staff',
      crypto.randomUUID(),
      {
        ...emptyEncounter(),
        name: 'Other tab',
      },
      {},
      null,
    );
    const raw = JSON.stringify(remote);
    localStorage.setItem(encounterDraftKey('staff'), raw);
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: encounterDraftKey('staff'),
        newValue: raw,
      }),
    );
    await flush();
    expect(editor.draft.pendingRecovery.value).toBeNull();
    expect(editor.locked.value).toBe(true);
    expect(editor.form.name).toBe('Recovered work');
    await editor.draft.overwriteConflict(true);
    const kept = JSON.parse(localStorage.getItem(encounterDraftKey('staff'))!);
    expect(kept.form.name).toBe('Recovered work');
    expect(kept.form.factions).toEqual(['fire']);
    expect(kept.form.entries).toEqual([{ card_id: 'a', quantity: 20 }]);
    expect(kept.draftId).not.toBe(original.draftId);
    expect(editor.locked.value).toBe(false);
  });
  test('an uncertain create displaced by another tab retries the immutable request without replacing that draft', async () => {
    const { editor, router } = await mount();
    editor.form.name = 'Original request';
    mocks.create.mockRejectedValueOnce(new Error('connection lost'));
    mocks.lookup.mockResolvedValue({ status: 'missing' });
    const creating = editor.save();
    await vi.advanceTimersByTimeAsync(3500);
    await creating;
    expect(editor.publication.isCreationUnknown.value).toBe(true);
    const remote = buildEncounterDraft(
      'staff',
      crypto.randomUUID(),
      {
        ...emptyEncounter(),
        name: 'Other tab',
      },
      {},
      null,
    );
    const raw = JSON.stringify(remote);
    localStorage.setItem(encounterDraftKey('staff'), raw);
    window.dispatchEvent(
      new StorageEvent('storage', {
        key: encounterDraftKey('staff'),
        newValue: raw,
      }),
    );
    expect(editor.draft.conflict.value?.kind).toBe('active-draft');
    await editor.publication.retry();
    expect(mocks.create).toHaveBeenCalledTimes(2);
    expect(mocks.create.mock.calls[1]).toEqual(mocks.create.mock.calls[0]);
    expect(localStorage.getItem(encounterDraftKey('staff'))).toBe(raw);
    expect(router.currentRoute.value.path).toBe('/my/encounters/saved/edit');
  });
  test.each(['replaced', 'removed'] as const)(
    'leaving a %s cross-tab draft requires confirmation without modifying the remote slot',
    async (change) => {
      const { editor, router } = await mount();
      editor.form.name = 'Unsaved local work';
      await editor.draft.persist();
      const raw =
        change === 'replaced'
          ? JSON.stringify(
              buildEncounterDraft(
                'staff',
                crypto.randomUUID(),
                {
                  ...emptyEncounter(),
                  name: 'Other tab',
                },
                {},
                null,
              ),
            )
          : null;
      if (raw === null) localStorage.removeItem(encounterDraftKey('staff'));
      else localStorage.setItem(encounterDraftKey('staff'), raw);
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: encounterDraftKey('staff'),
          newValue: raw,
        }),
      );
      const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
      await router.push('/my/encounters');
      expect(confirm).toHaveBeenCalledWith('Leave with unsaved changes?');
      expect(router.currentRoute.value.path).toBe('/my/encounters/new');
      expect(editor.form.name).toBe('Unsaved local work');
      confirm.mockReturnValue(true);
      await router.push('/my/encounters');
      expect(router.currentRoute.value.path).toBe('/my/encounters');
      expect(localStorage.getItem(encounterDraftKey('staff'))).toBe(raw);
    },
  );
  test('leaving a durable local draft does not ask to discard it', async () => {
    const { editor, router } = await mount();
    editor.form.name = 'Recoverable work';
    const confirm = vi.spyOn(window, 'confirm');
    await router.push('/my/encounters');
    expect(confirm).not.toHaveBeenCalled();
    expect(router.currentRoute.value.path).toBe('/my/encounters');
    expect(JSON.parse(localStorage.getItem(encounterDraftKey('staff'))!).form.name).toBe(
      'Recoverable work',
    );
  });
  test('cleanup failure after confirmed creation cannot cause a second create', async () => {
    const { editor, router } = await mount();
    editor.form.name = 'Created';
    const original = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (this: Storage, key, value) {
      if (value.includes('"kind":"retired"')) throw new Error('quota');
      original.call(this, key, value);
    });
    await editor.save();
    await editor.save();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.path).toBe('/my/encounters/saved/edit');
  });
  test('storage failure keeps editing and creation available in memory', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota');
    });
    const { editor, router } = await mount();
    editor.form.name = 'Memory draft';
    await editor.draft.persist();
    expect(editor.draft.storageUnavailable.value).toBe(true);
    await editor.save();
    expect(router.currentRoute.value.path).toBe('/my/encounters/saved/edit');
  });
  test('navigation failure after a committed create retries navigation without creating again', async () => {
    const { editor, router } = await mount();
    editor.form.name = 'Created';
    const removeGuard = router.beforeEach((to) => !to.path.endsWith('/saved/edit'));
    await editor.save();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(editor.publication.hasTerminalNavigationRetry.value).toBe(true);
    expect(router.currentRoute.value.path).toBe('/my/encounters/new');
    removeGuard();
    await editor.save();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.path).toBe('/my/encounters/saved/edit');
  });
  test('enabling autosync saves existing edits and remembers the preference on reload', async () => {
    const { editor } = await mount('/existing/saved');
    mocks.update.mockImplementation(async (_id, payload, revision) => ({
      ...saved(),
      ...payload,
      revision: revision + 1,
    }));
    editor.form.name = 'Autosaved Encounter';
    await vi.advanceTimersByTimeAsync(500);
    expect(mocks.update).not.toHaveBeenCalled();
    editor.autosync.value = true;
    await vi.advanceTimersByTimeAsync(500);
    expect(mocks.update).toHaveBeenCalledWith(
      'saved',
      expect.objectContaining({ name: 'Autosaved Encounter' }),
      1,
    );
    expect(editor.changeStatus.value).toBe('Saved');
    cleanup.splice(0).forEach((fn) => fn());
    const reopened = (await mount('/existing/saved')).editor;
    expect(reopened.autosync.value).toBe(true);
    reopened.form.description_markup = 'Changed details';
    await vi.advanceTimersByTimeAsync(500);
    expect(mocks.update).toHaveBeenCalledTimes(2);
  });
});

test('sideboards share board editing, preserve quantities on moves, and recover locally', async () => {
  const { editor } = await mount();
  editor.add(card('main'));
  editor.quantity('main', 20);
  editor.addSideboard();
  const boardId = editor.boards.activeBoardId.value;
  editor.renameSideboard(boardId, 'Reinforcements');
  editor.add(card('reserve'));
  editor.quantity('reserve', 3);
  editor.add(card('other'));
  editor.move(1, -1);
  editor.moveToBoard('reserve', 'mainboard');
  expect(editor.total.value).toBe(21);
  expect(editor.form.sideboards[0].entries).toEqual([
    { card_id: 'other', quantity: 1 },
    { card_id: 'reserve', quantity: 2 },
  ]);
  await vi.advanceTimersByTimeAsync(450);
  cleanup.splice(0).forEach((fn) => fn());
  const recovered = (await mount()).editor;
  await recovered.recover(recovered.draft.pendingRecovery.value!);
  expect(recovered.form.sideboards[0].name).toBe('Reinforcements');
  expect(recovered.form.sideboards[0].entries.map((entry) => entry.quantity)).toEqual([1, 2]);
  expect(recovered.cards.value.other.id).toBe('other');
  recovered.boards.selectBoard(boardId);
  recovered.removeSideboard(boardId);
  expect(recovered.boards.activeBoardId.value).toBe('mainboard');
  expect(recovered.total.value).toBe(21);
});

test('autosync adopts saved sideboard identity while keeping the selected board', async () => {
  const { editor } = await mount('/existing/saved');
  mocks.update.mockResolvedValue({
    ...saved(),
    revision: 2,
    sideboards: [
      {
        id: 'server-board',
        name: 'Sideboard 1',
        entries: [{ card_id: 'reserve', quantity: 1, card: card('reserve') }],
      },
    ],
  });
  editor.addSideboard();
  editor.add(card('reserve'));
  editor.autosync.value = true;
  await vi.advanceTimersByTimeAsync(450);
  expect(editor.boards.activeBoardId.value).toBe('server-board');
  expect(editor.form.sideboards[0].source_id).toBe('server-board');
  expect(editor.dirty.value).toBe(false);
  await vi.advanceTimersByTimeAsync(500);
  expect(mocks.update).toHaveBeenCalledTimes(1);
});

test('legacy draft recovery adds empty sideboards without changing an uncertain payload', async () => {
  const legacy = { ...emptyEncounter(), name: 'Legacy' };
  delete (legacy as Partial<typeof legacy>).sideboards;
  const stored = buildEncounterDraft('staff', 'legacy-key', emptyEncounter(), {}, null);
  stored.form = legacy;
  stored.pendingCreateAttempt = {
    payload: legacy,
    signature: JSON.stringify(legacy),
    startedAt: new Date().toISOString(),
  };
  localStorage.setItem(encounterDraftKey('staff'), JSON.stringify(stored));
  mocks.lookup.mockResolvedValue({ status: 'missing' });
  const { editor } = await mount();
  const recovery = editor.recover(editor.draft.pendingRecovery.value!);
  await vi.advanceTimersByTimeAsync(4000);
  await recovery;
  expect(editor.form.sideboards).toEqual([]);
  expect(editor.publication.attempt.value?.payload).not.toHaveProperty('sideboards');
});

test('reloading a sideboard deleted by another staff member returns to the mainboard', async () => {
  mocks.fetch.mockResolvedValue({
    ...saved(),
    sideboards: [{ id: 'reserve', name: 'Reserve', entries: [] }],
  });
  const { editor } = await mount('/existing/saved');
  editor.boards.selectBoard('reserve');
  mocks.fetch.mockResolvedValue({ ...saved(), revision: 2 });
  await editor.reload();
  expect(editor.boards.activeBoardId.value).toBe('mainboard');
  editor.add(card('new-card'));
  expect(editor.form.entries).toEqual([{ card_id: 'new-card', quantity: 1 }]);
});

test('loading another local draft clears a deleted sideboard selection', async () => {
  const { editor } = await mount();
  editor.addSideboard();
  const remote = buildEncounterDraft(
    'staff',
    editor.draft.draftId.value,
    emptyEncounter(),
    {},
    null,
  );
  await editor.recover(remote);
  expect(editor.boards.activeBoardId.value).toBe('mainboard');
  editor.add(card('new-card'));
  expect(editor.form.entries).toEqual([{ card_id: 'new-card', quantity: 1 }]);
});

test('endorsement during autosave stops further saves and retains every local board', async () => {
  const { editor } = await mount('/existing/saved');
  editor.setDetails({ name: 'Local changes', visibility: 'unlisted' });
  editor.addSideboard();
  editor.add(card('reserve'));
  mocks.update.mockRejectedValue({
    isAxiosError: true,
    response: { status: 403, data: { detail: 'Only staff may edit this Official Encounter.' } },
  });
  editor.autosync.value = true;
  await vi.advanceTimersByTimeAsync(500);
  expect(editor.readOnly.value).toBe(true);
  expect(editor.locked.value).toBe(true);
  expect(editor.autosync.value).toBe(false);
  expect(editor.form.name).toBe('Local changes');
  expect(editor.form.sideboards[0].entries).toEqual([{ card_id: 'reserve', quantity: 1 }]);
  expect(editor.dirty.value).toBe(true);
  editor.autosync.value = true;
  await vi.advanceTimersByTimeAsync(1500);
  await editor.save();
  expect(mocks.update).toHaveBeenCalledTimes(1);
});

test('ordinary owner payload omits Official status while staff can change it', async () => {
  const { editor } = await mount('/existing/saved');
  expect(editor.form).not.toHaveProperty('is_official');
  editor.setDetails({ is_official: true });
  expect(editor.form).not.toHaveProperty('is_official');
  editor.setDetails({ name: 'Owner edit' });
  mocks.update.mockResolvedValue({ ...saved(), name: 'Owner edit', revision: 2 });
  await editor.save();
  expect(mocks.update.mock.calls[0][1]).not.toHaveProperty('is_official');
  mocks.auth.canAccessStaffRoutes = true;
  await editor.reload();
  expect(editor.form.is_official).toBe(false);
  editor.setDetails({ is_official: true });
  expect(editor.form.is_official).toBe(true);
});

test('reconciliation opens an endorsed creation read only without another create', async () => {
  const legacy = emptyEncounter();
  const stored = buildEncounterDraft('staff', 'pending-key', legacy, {}, null);
  stored.pendingCreateAttempt = {
    payload: legacy,
    signature: JSON.stringify(legacy),
    startedAt: new Date().toISOString(),
  };
  localStorage.setItem(encounterDraftKey('staff'), JSON.stringify(stored));
  mocks.lookup.mockResolvedValue({
    status: 'found',
    record: { ...saved(), is_official: true, can_edit: false, can_delete: false },
  });
  const { editor, router } = await mount();
  await editor.recover(editor.draft.pendingRecovery.value!);
  await flush();
  expect(router.currentRoute.value.path).toBe('/encounters/saved');
  expect(mocks.create).not.toHaveBeenCalled();
});

test('opening an official record locks owner mutations and unmarking restores editing', async () => {
  mocks.fetch.mockResolvedValue({
    ...saved(),
    is_official: true,
    can_edit: false,
    can_delete: false,
  });
  const { editor } = await mount('/existing/saved');
  expect(editor.readOnly.value).toBe(true);
  editor.add(card('blocked'));
  editor.addSideboard();
  editor.setDetails({ name: 'Blocked' });
  expect(editor.form.entries).toEqual([]);
  expect(editor.form.sideboards).toEqual([]);
  expect(editor.form.name).toBe('');
  mocks.fetch.mockResolvedValue({ ...saved(), revision: 3 });
  await editor.reload();
  expect(editor.readOnly.value).toBe(false);
  editor.setDetails({ name: 'Restored' });
  expect(editor.form.name).toBe('Restored');
});

test('recovering older drafts clears any prior Official selection without adding it to owner payloads', async () => {
  mocks.auth.canAccessStaffRoutes = true;
  const { editor } = await mount();
  editor.setDetails({ is_official: true });
  const stored = buildEncounterDraft(
    'staff',
    editor.draft.draftId.value,
    emptyEncounter(),
    {},
    null,
  );
  await editor.recover(stored);
  expect(editor.form).not.toHaveProperty('is_official');
  mocks.auth.canAccessStaffRoutes = false;
  stored.form.is_official = false;
  await editor.recover(stored);
  expect(editor.form).not.toHaveProperty('is_official');
  expect(stored.form.is_official).toBe(false);
});
