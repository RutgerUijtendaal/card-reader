import { effectScope, nextTick } from 'vue';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { useCardBackImport } from '@/features/admin/composables/useCardBackImport';
import type { ImportHero } from '@/features/admin/composables/useCardBackImport';
import type { CardBackImportResult, CardBackRecord } from '@/domain/card-backs/types';
import { cardBackLabel, suggestHero } from '@/features/admin/utils/cardBackImport';

const { fetchCards, fetchCard, send, lookup } = vi.hoisted(() => ({
  fetchCards: vi.fn(), fetchCard: vi.fn(), send: vi.fn(), lookup: vi.fn(),
}));
vi.mock('@/domain/cards/api', () => ({ fetchCards, fetchCard }));
vi.mock('@/domain/card-backs/api', () => ({ importCardBack: send, fetchCardBackImportResult: lookup }));
const scopes: ReturnType<typeof effectScope>[] = [];
const setup = () => {
  const scope = effectScope();
  scopes.push(scope);
  return scope.run(useCardBackImport)!;
};
const hero = (id = 'hero', override: string | null = null): ImportHero => ({
  id, name: 'Silver Knight', card_pool: 'player', card_roles: ['hero'], lifecycle_status: 'active',
  card_back_override_id: override, effective_card_back: null,
} as ImportHero);
const success = (): CardBackImportResult => ({
  outcome: 'succeeded', asset: { id: 'back' } as CardBackRecord, hero_card_id: null,
});
const file = (name = 'Silver_Knight.png') => new File(['image'], name, { type: 'image/png' });
const deferred = <T>() => {
  let resolve!: (result: T) => void;
  const promise = new Promise<T>((next) => { resolve = next; });
  return { promise, resolve };
};
beforeEach(() => {
  vi.resetAllMocks();
  URL.createObjectURL = vi.fn(() => 'blob:preview');
  URL.revokeObjectURL = vi.fn();
  fetchCards.mockResolvedValue({ results: [hero()], next_page: null });
  fetchCard.mockResolvedValue(hero());
  send.mockResolvedValue(success());
  lookup.mockRejectedValue(new Error('not found'));
});
afterEach(() => scopes.splice(0).forEach((scope) => scope.stop()));

describe('card-back import preparation', () => {
  test('prepares seventy labeled images without assigning suggestions', async () => {
    const flow = setup();
    flow.addFiles(Array.from({ length: 70 }, (_, index) => file(index ? `Hero-${index}.png` : 'Silver_Knight.png')));
    await flow.loadHeroes();
    expect(flow.rows.value).toHaveLength(70);
    expect(flow.rows.value[0]?.label).toBe('Silver Knight');
    expect(flow.rows.value.every((row) => row.selection.kind === 'none')).toBe(true);
    expect(suggestHero('Silver_Knight.png', flow.heroes.value)?.id).toBe('hero');
    expect(send).not.toHaveBeenCalled();
    await flow.submit();
    expect(send).toHaveBeenCalledTimes(70);
    expect(new Set(send.mock.calls.map(([attempt]) => attempt.clientRequestId)).size).toBe(70);
    expect(flow.rows.value.every((row) => row.state.kind === 'succeeded')).toBe(true);
    expect(flow.hasUnsaved.value).toBe(false);
  });
  test('completes pagination across all pools before offering matches', async () => {
    const flow = setup();
    const last = deferred<{ results: ImportHero[]; next_page: null }>();
    fetchCards.mockResolvedValueOnce({ results: [hero()], next_page: 2 }).mockReturnValueOnce(last.promise);
    const loading = flow.loadHeroes();
    await nextTick();
    expect(flow.catalog.value).toBe('loading');
    expect(flow.heroes.value).toEqual([]);
    last.resolve({ results: [{ ...hero('other'), card_pool: 'evil' }], next_page: null });
    await loading;
    expect(suggestHero('silver-knight.png', flow.heroes.value)).toBeNull();
    expect(fetchCards).toHaveBeenLastCalledWith(expect.objectContaining({
      page: 2, card_roles: 'hero', lifecycle_status: 'active', show_groups: false,
    }));
    expect(fetchCards.mock.calls[0]?.[0]).not.toHaveProperty('card_pool');
  });
  test('does not offer partial candidates after a catalog failure', async () => {
    const flow = setup();
    fetchCards.mockResolvedValueOnce({ results: [hero()], next_page: 2 }).mockRejectedValueOnce(new Error());
    await flow.loadHeroes();
    expect(flow.catalog.value).toBe('error');
    expect(flow.heroes.value).toEqual([]);
  });
  test('normalizes filenames without fuzzy matching or stripping meaningful suffixes', () => {
    expect(cardBackLabel('Silver-Knight.webp')).toBe('Silver Knight');
    expect(suggestHero('Silver_Knight_BACK.png', [hero()])).toBeNull();
    expect(suggestHero(' SILVER_Knight.png', [hero()])?.id).toBe('hero');
  });
  test('requires explicit replacement confirmation and keeps custom labels', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    const row = flow.rows.value[0]!;
    row.label = 'My custom label';
    fetchCard.mockResolvedValue(hero('hero', 'old'));
    await flow.selectHero(row, 'hero');
    expect(flow.canSubmit.value).toBe(false);
    expect(row.label).toBe('My custom label');
    if (row.selection.kind !== 'selected') throw new Error('expected selected hero');
    row.selection.replacementConfirmed = true;
    expect(flow.canSubmit.value).toBe(true);
    await flow.submit();
    expect(send).toHaveBeenCalledWith(expect.objectContaining({
      label: 'My custom label', heroCardId: 'hero', expectedOverrideId: 'old',
    }));
  });
  test('clearing or reselecting a hero clears the replacement confirmation', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    const row = flow.rows.value[0]!;
    fetchCard.mockResolvedValue(hero('hero', 'old'));
    await flow.selectHero(row, 'hero');
    if (row.selection.kind !== 'selected') throw new Error();
    row.selection.replacementConfirmed = true;
    await flow.selectHero(row, null);
    await flow.selectHero(row, 'hero');
    expect(row.selection).toMatchObject({ replacementConfirmed: false });
  });
  test('blocks duplicate hero targets, missing labels and invalid files', async () => {
    const flow = setup();
    flow.addFiles([file(), file('second.png')]);
    await flow.selectHero(flow.rows.value[0]!, 'hero');
    await flow.selectHero(flow.rows.value[1]!, 'hero');
    expect(flow.rowError(flow.rows.value[0]!)).toContain('more than once');
    flow.removeRow(flow.rows.value[1]!);
    flow.rows.value[0]!.label = ' ';
    expect(flow.canSubmit.value).toBe(false);
    flow.addFiles([file('invalid.txt')]);
    expect(flow.rowError(flow.rows.value[1]!)).toContain('Choose PNG');
  });
});

describe('card-back import outcomes', () => {
  test('captures the entire batch before sending and prevents double submission', async () => {
    const flow = setup();
    flow.addFiles([file(), file('second.png')]);
    const first = deferred<CardBackImportResult>();
    send.mockReturnValueOnce(first.promise);
    const saving = flow.submit();
    await flow.submit();
    flow.rows.value[1]!.label = 'changed programmatically';
    flow.addFiles([file()]);
    expect(flow.rows.value).toHaveLength(2);
    expect(flow.unresolved.value).toBe(true);
    first.resolve(success());
    await saving;
    expect(send.mock.calls[1]?.[0].label).toBe('second');
  });
  test('continues past a rejected row and never resubmits completed rows', async () => {
    const flow = setup();
    flow.addFiles([file(), file('second.png')]);
    send.mockResolvedValueOnce({ outcome: 'rejected', detail: 'Bad image' });
    await flow.submit();
    expect(flow.rows.value.map((row) => row.state.kind)).toEqual(['rejected', 'succeeded']);
    await flow.submit();
    expect(send).toHaveBeenCalledTimes(3);
    expect(send.mock.calls[2]?.[0].clientRequestId).not.toBe(send.mock.calls[0]?.[0].clientRequestId);
  });
  test('requires fresh hero review after a stale-assignment rejection', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    await flow.selectHero(flow.rows.value[0]!, 'hero');
    send.mockResolvedValueOnce({ outcome: 'rejected', detail: 'Assignment changed' });
    await flow.submit();
    expect(flow.rows.value[0]?.selection.kind).toBe('error');
    expect(flow.canSubmit.value).toBe(false);
    await flow.selectHero(flow.rows.value[0]!, null);
    expect(flow.canSubmit.value).toBe(true);
  });
  test('reconciles a lost response without repeating a successful mutation', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    send.mockRejectedValue(new Error('timeout'));
    lookup.mockResolvedValue(success());
    await flow.submit();
    expect(flow.rows.value[0]?.state.kind).toBe('succeeded');
    expect(send).toHaveBeenCalledTimes(1);
    expect(flow.unresolved.value).toBe(false);
  });
  test('retains unresolved payloads on lookup misses and retries the same key', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    send.mockRejectedValueOnce(new Error('timeout'));
    await flow.submit();
    const row = flow.rows.value[0]!;
    expect(row.state.kind).toBe('uncertain');
    expect(flow.canSubmit.value).toBe(false);
    expect(flow.hasUnsaved.value).toBe(true);
    flow.removeRow(row);
    await flow.selectHero(row, 'hero');
    expect(flow.rows.value).toHaveLength(1);
    expect(fetchCard).not.toHaveBeenCalled();
    await flow.retry(row);
    expect(send.mock.calls[1]?.[0]).toBe(send.mock.calls[0]?.[0]);
    expect(row.state.kind).toBe('succeeded');
  });
  test('a lookup error cannot hide an authoritative retry success', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    send.mockRejectedValueOnce(new Error('timeout'));
    await flow.submit();
    await flow.retry(flow.rows.value[0]!);
    expect(flow.rows.value[0]?.state.kind).toBe('succeeded');
    expect(flow.hasUnsaved.value).toBe(false);
  });
  test('a used key whose asset was deleted is terminal and is not re-created', async () => {
    const flow = setup();
    flow.addFiles([file()]);
    send.mockResolvedValue({ outcome: 'deleted', detail: 'Deleted' });
    await flow.submit();
    expect(flow.rows.value[0]?.state.kind).toBe('deleted');
    expect(flow.canSubmit.value).toBe(false);
  });
});
