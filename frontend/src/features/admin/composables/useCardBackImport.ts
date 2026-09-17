import { computed, onScopeDispose, ref } from 'vue';
import { isAxiosError } from 'axios';
import { fetchCard, fetchCards } from '@/domain/cards/api';
import { fetchCardBackImportResult, importCardBack } from '@/domain/card-backs/api';
import type { CardListItem, PaginatedCardsResponse } from '@/domain/cards/types';
import type { CardBackImportAttempt, CardBackImportResult, CardBackSelectionFields } from '@/domain/card-backs/types';
import { cardBackFileError, cardBackLabel } from '@/features/admin/utils/cardBackImport';

export type ImportHero = CardListItem & CardBackSelectionFields;
type HeroSelection =
  | { kind: 'none' }
  | { kind: 'loading'; id: string }
  | { kind: 'selected'; hero: ImportHero; replacementConfirmed: boolean }
  | { kind: 'error'; message: string };
type RowState =
  | { kind: 'editing' }
  | { kind: 'submitting' | 'uncertain'; attempt: CardBackImportAttempt }
  | { kind: 'rejected'; message: string }
  | { kind: 'succeeded'; result: Extract<CardBackImportResult, { outcome: 'succeeded' }> }
  | { kind: 'deleted'; message: string };
export type CardBackImportRow = {
  id: string;
  file: File;
  previewUrl: string;
  label: string;
  selection: HeroSelection;
  state: RowState;
};
export const isEditableRow = (row: CardBackImportRow): boolean =>
  row.state.kind === 'editing' || row.state.kind === 'rejected';

export const useCardBackImport = () => {
  const rows = ref<CardBackImportRow[]>([]);
  const heroes = ref<CardListItem[]>([]);
  const catalog = ref<'loading' | 'ready' | 'error'>('loading');
  const running = ref(false);
  const selectionRequests = new Map<string, number>();
  const pending = computed(() => rows.value.filter(isEditableRow));
  const unresolved = computed(() => rows.value.some((row) =>
    row.state.kind === 'submitting' || row.state.kind === 'uncertain'));
  const hasUnsaved = computed(() => rows.value.some((row) => isEditableRow(row)
    || row.state.kind === 'uncertain' || row.state.kind === 'submitting'));
  const usedHeroIds = computed(() => rows.value.filter((row) =>
    row.state.kind !== 'succeeded' && row.state.kind !== 'deleted').flatMap((row) =>
    row.selection.kind === 'selected' ? [row.selection.hero.id] : []));

  const loadHeroes = async (): Promise<void> => {
    catalog.value = 'loading';
    try {
      const loaded: CardListItem[] = [];
      let page: number | null = 1;
      while (page !== null) {
        const response: PaginatedCardsResponse<CardListItem> = await fetchCards<CardListItem>({
          card_roles: 'hero', lifecycle_status: 'active', show_groups: false, page, page_size: 100,
        });
        loaded.push(...response.results);
        page = response.next_page;
      }
      heroes.value = loaded;
      catalog.value = 'ready';
    } catch {
      heroes.value = [];
      catalog.value = 'error';
    }
  };

  const addFiles = (files: File[]): void => {
    if (running.value) return;
    rows.value.push(...files.map((file): CardBackImportRow => ({
      id: crypto.randomUUID(), file, previewUrl: URL.createObjectURL(file),
      label: cardBackLabel(file.name), selection: { kind: 'none' }, state: { kind: 'editing' },
    })));
  };
  const removeRow = (row: CardBackImportRow): void => {
    if (running.value || !isEditableRow(row)) return;
    URL.revokeObjectURL(row.previewUrl);
    rows.value = rows.value.filter((item) => item.id !== row.id);
  };
  const selectHero = async (row: CardBackImportRow, heroId: string | null): Promise<void> => {
    if (running.value || !isEditableRow(row)) return;
    const selectionRequest = (selectionRequests.get(row.id) ?? 0) + 1;
    selectionRequests.set(row.id, selectionRequest);
    if (heroId === null) {
      row.selection = { kind: 'none' };
      return;
    }
    const selection: HeroSelection = { kind: 'loading', id: heroId };
    row.selection = selection;
    try {
      const hero = await fetchCard<ImportHero>(heroId);
      if (selectionRequests.get(row.id) !== selectionRequest) return;
      if (!hero.card_roles.includes('hero') || hero.lifecycle_status !== 'active'
        || hero.card_back_override_id === undefined) {
        row.selection = { kind: 'error', message: 'This hero is no longer available. Choose again.' };
        return;
      }
      row.selection = { kind: 'selected', hero, replacementConfirmed: false };
    } catch {
      if (selectionRequests.get(row.id) === selectionRequest) {
        row.selection = { kind: 'error', message: 'Could not load this hero. Choose again.' };
      }
    }
  };
  const rowError = (row: CardBackImportRow): string => {
    const fileError = cardBackFileError(row.file);
    if (fileError) return fileError;
    if (!row.label.trim()) return 'A label is required.';
    if (row.selection.kind === 'loading') return 'Loading the current hero assignment…';
    if (row.selection.kind === 'error') return row.selection.message;
    if (row.selection.kind === 'selected') {
      const { hero, replacementConfirmed } = row.selection;
      if (usedHeroIds.value.filter((id) => id === hero.id).length > 1) {
        return 'This hero is selected more than once.';
      }
      if (hero.card_back_override_id !== null && !replacementConfirmed) {
        return 'Confirm replacing this hero’s existing override.';
      }
    }
    return '';
  };
  const canSubmit = computed(() => !running.value && !unresolved.value
    && pending.value.length > 0 && pending.value.every((row) => !rowError(row)));

  const acceptResult = (row: CardBackImportRow, result: CardBackImportResult): void => {
    if (result.outcome === 'succeeded') row.state = { kind: 'succeeded', result };
    else if (result.outcome === 'deleted') row.state = { kind: 'deleted', message: result.detail };
    else {
      row.state = { kind: 'rejected', message: result.detail };
      // Fresh selection is required after a rejected assignment, not a stale confirmation.
      if (row.selection.kind === 'selected') {
        row.selection = { kind: 'error', message: 'Review and select the hero again, or choose Library only.' };
      }
    }
  };
  const reconcile = async (row: CardBackImportRow, attempt: CardBackImportAttempt): Promise<void> => {
    let result: CardBackImportResult;
    try {
      result = await fetchCardBackImportResult(attempt.clientRequestId);
    } catch {
      row.state = { kind: 'uncertain', attempt };
      return;
    }
    acceptResult(row, result);
  };
  const send = async (row: CardBackImportRow, attempt: CardBackImportAttempt, retry = false): Promise<void> => {
    row.state = { kind: 'submitting', attempt };
    let result: CardBackImportResult;
    try {
      result = await importCardBack(attempt);
    } catch (error) {
      if (!retry && isAxiosError(error) && [401, 403].includes(error.response?.status ?? 0)) {
        row.state = { kind: 'rejected', message: 'Staff access is required. Sign in again before retrying.' };
      } else if (!retry && isAxiosError(error) && error.response?.status === 400
        && error.response.data?.outcome === 'invalid') {
        row.state = { kind: 'rejected', message: 'The request was invalid. Review its label and hero selection.' };
      } else {
        await reconcile(row, attempt);
      }
      return;
    }
    acceptResult(row, result);
  };
  const submit = async (): Promise<void> => {
    if (!canSubmit.value) return;
    running.value = true;
    // Capture every row before starting, so the reviewed batch stays immutable.
    const batch = pending.value.map((row) => ({
      row,
      attempt: Object.freeze({
        clientRequestId: crypto.randomUUID(), file: row.file, label: row.label.trim(),
        heroCardId: row.selection.kind === 'selected' ? row.selection.hero.id : null,
        expectedOverrideId: row.selection.kind === 'selected' ? row.selection.hero.card_back_override_id : null,
      }),
    }));
    try {
      for (const { row, attempt } of batch) await send(row, attempt);
    } finally {
      running.value = false;
    }
  };
  const retry = async (row: CardBackImportRow): Promise<void> => {
    if (running.value || row.state.kind !== 'uncertain') return;
    const attempt = row.state.attempt;
    running.value = true;
    row.state = { kind: 'submitting', attempt };
    try {
      await reconcile(row, attempt);
      if (row.state.kind === 'uncertain') await send(row, attempt, true);
    } finally {
      running.value = false;
    }
  };
  onScopeDispose(() => rows.value.forEach((row) => URL.revokeObjectURL(row.previewUrl)));
  return {
    rows, heroes, catalog, running, pending, unresolved, hasUnsaved, usedHeroIds,
    loadHeroes, addFiles, removeRow, selectHero, rowError, canSubmit, submit, retry,
  };
};
