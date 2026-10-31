/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick } from 'vue';
import { createMemoryHistory, createRouter } from 'vue-router';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import type { CardListItem, GalleryItem } from '@/domain/cards/types';
import { emptyEncounter, type EncounterRecord } from '@/domain/encounters/types';
import { buildEncounterDraft, encounterDraftKey } from '../utils/draftStorage';
import { useEncounterEditor } from './useEncounterEditor';

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  lookup: vi.fn(),
  fetch: vi.fn(),
  update: vi.fn(),
  card: vi.fn(),
}));
vi.mock('@/domain/session/store', () => ({ useAuthStore: () => ({ user: { id: 'staff' } }) }));
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
  revision: 1,
  description: '',
  long_description: '',
  boss_card: null,
  boss_cards: [],
  entries: [],
  total_cards: 0,
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
const mount = async (path = '/staff/encounters/new') => {
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
      { path: '/staff/encounters/new', component: view },
      { path: '/staff/encounters/:id/edit', component: { template: '<div />' } },
      { path: '/staff/encounters', component: { template: '<div />' } },
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
      expect(router.currentRoute.value.path).toBe('/staff/encounters/saved/edit');
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
    expect(router.currentRoute.value.path).toBe('/staff/encounters/saved/edit');
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
    expect(router.currentRoute.value.path).toBe('/staff/encounters');
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
    const original = buildEncounterDraft('staff', crypto.randomUUID(), {
      ...emptyEncounter(),
      name: 'Recovered work',
      factions: ['fire'],
      entries: [{ card_id: 'a', quantity: 20 }],
    }, { a: card('a') }, null);
    localStorage.setItem(encounterDraftKey('staff'), JSON.stringify(original));
    const { editor } = await mount();
    expect(editor.draft.pendingRecovery.value).not.toBeNull();
    const remote = buildEncounterDraft('staff', crypto.randomUUID(), {
      ...emptyEncounter(), name: 'Other tab',
    }, {}, null);
    const raw = JSON.stringify(remote);
    localStorage.setItem(encounterDraftKey('staff'), raw);
    window.dispatchEvent(new StorageEvent('storage', {
      key: encounterDraftKey('staff'), newValue: raw,
    }));
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
    const remote = buildEncounterDraft('staff', crypto.randomUUID(), {
      ...emptyEncounter(), name: 'Other tab',
    }, {}, null);
    const raw = JSON.stringify(remote);
    localStorage.setItem(encounterDraftKey('staff'), raw);
    window.dispatchEvent(new StorageEvent('storage', {
      key: encounterDraftKey('staff'), newValue: raw,
    }));
    expect(editor.draft.conflict.value?.kind).toBe('active-draft');
    await editor.publication.retry();
    expect(mocks.create).toHaveBeenCalledTimes(2);
    expect(mocks.create.mock.calls[1]).toEqual(mocks.create.mock.calls[0]);
    expect(localStorage.getItem(encounterDraftKey('staff'))).toBe(raw);
    expect(router.currentRoute.value.path).toBe('/staff/encounters/saved/edit');
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
    expect(router.currentRoute.value.path).toBe('/staff/encounters/saved/edit');
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
    expect(router.currentRoute.value.path).toBe('/staff/encounters/saved/edit');
  });
  test('navigation failure after a committed create retries navigation without creating again', async () => {
    const { editor, router } = await mount();
    editor.form.name = 'Created';
    const removeGuard = router.beforeEach((to) => !to.path.endsWith('/saved/edit'));
    await editor.save();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(editor.publication.hasTerminalNavigationRetry.value).toBe(true);
    expect(router.currentRoute.value.path).toBe('/staff/encounters/new');
    removeGuard();
    await editor.save();
    expect(mocks.create).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.path).toBe('/staff/encounters/saved/edit');
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
