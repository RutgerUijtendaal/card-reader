import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useDebounceFn, useEventListener, useLocalStorage } from '@vueuse/core';
import { isNavigationFailure, onBeforeRouteLeave, useRoute, useRouter } from 'vue-router';
import { isAxiosError } from 'axios';
import { toast } from 'vue-sonner';
import { useAuthStore } from '@/domain/session/store';
import { fetchCard } from '@/domain/cards/api';
import type { CardListItem, GalleryItem } from '@/domain/cards/types';
import type { CardFaction } from '@/domain/cards/cardFactions';
import {
  createEncounter,
  fetchEncounter,
  fetchEncounterRules,
  lookupEncounterCreation,
  updateEncounter,
} from '@/domain/encounters/api';
import {
  emptyEncounter,
  encounterDraftFromRecord,
  type EncounterRecord,
} from '@/domain/encounters/types';
import { getApiErrorMessage } from '@/shared/api/errors';
import { useLocalDraft } from '@/shared/drafts/useLocalDraft';
import { useDraftCreation } from '@/shared/drafts/useDraftCreation';
import { isDeckMutationLocked } from '@/shared/drafts/lifecycle';
import {
  buildEncounterDraft,
  createEncounterDraftStorage,
  encounterDraftKey,
  parseEncounterDraft,
  type EncounterStoredDraft,
} from '../utils/draftStorage';

export const useEncounterEditor = () => {
  const route = useRoute();
  const router = useRouter();
  const auth = useAuthStore();
  const id = typeof route.params.id === 'string' ? route.params.id : null;
  const form = reactive(emptyEncounter());
  const cards = ref<Record<string, CardListItem>>({});
  const record = ref<EncounterRecord | null>(null);
  const mode = ref<'boss' | 'details' | 'cards'>('cards');
  const factions = ref<CardFaction[]>([]);
  const minimum = ref(20);
  const loading = ref(true);
  const saving = ref(false);
  const serverConflict = ref(false);
  const recoveryBusy = ref(false);
  const openingConfirmedRecord = ref(false);
  let bossSelection = 0;
  const error = ref('');
  const savedSignature = ref('');
  const autosync = useLocalStorage('card-reader.encounter-editor.autosync', false);
  const signature = computed(() => JSON.stringify(form));
  const draft = useLocalDraft({
    resourceLabel: 'Encounter',
    ownerId: String(auth.user?.id ?? ''),
    enabled: !id,
    form,
    cardLookup: cards,
    contentSignature: signature,
    emptyContentSignature: JSON.stringify(emptyEncounter()),
    storage: createEncounterDraftStorage(),
    key: encounterDraftKey,
    parse: parseEncounterDraft,
    build: buildEncounterDraft,
  });
  const applyRecord = (value: EncounterRecord) => {
    record.value = value;
    Object.assign(form, encounterDraftFromRecord(value));
    cards.value = Object.fromEntries(
      [
        ...(value.boss_card ? [value.boss_card] : []),
        ...value.boss_cards,
        ...value.entries.map((entry) => entry.card),
      ].map((card) => [card.id, card]),
    );
    factions.value = [...(value.boss_card?.card_factions ?? [])];
    savedSignature.value = signature.value;
    serverConflict.value = false;
  };
  const publication = useDraftCreation({
    resourceLabel: 'encounter',
    createRequest: createEncounter,
    lookupRequest: lookupEncounterCreation,
    persistenceState: draft.persistenceState,
    draftId: draft.draftId,
    payloadSignature: signature,
    buildPayload: () => JSON.parse(signature.value) as typeof form,
    validate: async () => true,
    persistAttempt: draft.persist,
    retireAfterCreation: draft.retireAfterCreation,
    discardAfterDeletedCreation: draft.discardAfterDeletedCreation,
    onSuccess: async (value) => {
      const result = await router.replace(`/staff/encounters/${value.id}/edit`);
      if (isNavigationFailure(result))
        throw new Error('Encounter created; navigation was interrupted.');
    },
    onDeleted: async () => {
      toast.info('The Encounter created from this draft was deleted.');
      const result = await router.replace('/staff/encounters');
      if (isNavigationFailure(result))
        throw new Error('Deleted creation confirmed; navigation was interrupted.');
    },
  });
  const locked = computed(
    () =>
      loading.value ||
      saving.value ||
      recoveryBusy.value ||
      serverConflict.value ||
      publication.hasTerminalNavigationRetry.value ||
      isDeckMutationLocked(draft.persistenceState.value, publication.creationState.value),
  );
  const dirty = computed(() => signature.value !== savedSignature.value);
  const total = computed(() => form.entries.reduce((sum, entry) => sum + entry.quantity, 0));
  const boss = computed(() => (form.boss_card_id ? cards.value[form.boss_card_id] : null));
  const issues = computed(() => {
    const messages = [];
    if (!form.name.trim()) messages.push('Name is required.');
    if (!boss.value) messages.push('Select a boss.');
    if (total.value < minimum.value)
      messages.push(`Add at least ${minimum.value} deck cards, excluding boss cards.`);
    if (!dirty.value && record.value) return record.value.status.issues;
    return messages;
  });
  const hydrate = async () => {
    const ids = [
      ...new Set(
        [form.boss_card_id, ...form.entries.map((entry) => entry.card_id)].filter(
          (value): value is string => !!value,
        ),
      ),
    ];
    const results = await Promise.allSettled(ids.map((cardId) => fetchCard<CardListItem>(cardId)));
    const resolvedIds = new Map<string, string>();
    results.forEach((result, index) => {
      if (result.status !== 'fulfilled') return;
      cards.value[result.value.id] = result.value;
      resolvedIds.set(ids[index], result.value.id);
    });
    // Keep uncertain create payloads immutable; reconcile merges only for editable drafts.
    if (!publication.attempt.value) {
      if (form.boss_card_id)
        form.boss_card_id = resolvedIds.get(form.boss_card_id) ?? form.boss_card_id;
      const entries = new Map<string, number>();
      form.entries.forEach((entry) => {
        const cardId = resolvedIds.get(entry.card_id) ?? entry.card_id;
        entries.set(cardId, (entries.get(cardId) ?? 0) + entry.quantity);
      });
      form.entries = [...entries].map(([card_id, quantity]) => ({ card_id, quantity }));
    }
    if (results.some((result) => result.status === 'rejected'))
      error.value =
        'Some cards could not be refreshed. Saved previews remain available; retry before publishing.';
  };
  const recover = async (stored: EncounterStoredDraft) => {
    recoveryBusy.value = true;
    draft.beginRecoveredDraft(stored);
    Object.assign(form, stored.form);
    cards.value = { ...stored.cards };
    try {
      // Reconcile the authoritative create independently of optional card hydration.
      if (stored.pendingCreateAttempt)
        await publication.recoverPendingAttempt(stored.pendingCreateAttempt);
      await hydrate();
      factions.value = [...(boss.value?.card_factions ?? [])];
    } finally {
      draft.completeRecovery();
      recoveryBusy.value = false;
    }
  };
  watch(draft.recoveryConflictCandidate, (stored) => {
    if (!stored) return;
    // The recovery dialog has not applied this candidate yet. Keep it as the
    // local side of the conflict without replacing the observed remote slot.
    Object.assign(form, stored.form);
    cards.value = { ...stored.cards };
    recoveryBusy.value = true;
    void (async () => {
      try {
        if (stored.pendingCreateAttempt)
          await publication.recoverPendingAttempt(stored.pendingCreateAttempt);
        await hydrate();
        factions.value = [...(boss.value?.card_factions ?? [])];
      } finally {
        recoveryBusy.value = false;
      }
    })();
  }, { flush: 'sync' });
  const loadConflict = async () => {
    const stored = draft.loadConflictDraft();
    if (stored) await recover(stored);
  };
  const openCreated = async () => {
    const conflict = draft.conflict.value;
    if (conflict?.slot.kind !== 'retired') return;
    recoveryBusy.value = true;
    try {
      const result = await lookupEncounterCreation(conflict.slot.marker.draftId);
      if (result.status === 'found') {
        openingConfirmedRecord.value = true;
        await router.push(`/staff/encounters/${result.record.id}/edit`);
      } else if (result.status === 'deleted') await draft.overwriteConflict(true);
      else error.value = 'Creation is not confirmed yet. Try again.';
    } catch (cause) {
      error.value = getApiErrorMessage(cause, 'Could not confirm creation.');
    } finally {
      recoveryBusy.value = false;
      openingConfirmedRecord.value = false;
    }
  };
  const reload = async () => {
    if (!id) return;
    loading.value = true;
    try {
      applyRecord(await fetchEncounter(id));
      error.value = '';
    } catch (cause) {
      error.value = getApiErrorMessage(cause, 'Could not load Encounter.');
    } finally {
      loading.value = false;
    }
  };
  const save = async () => {
    if (publication.hasTerminalNavigationRetry.value) {
      await publication.create();
      return;
    }
    if (locked.value) return;
    error.value = '';
    if (!id) {
      await publication.create();
      return;
    }
    if (!record.value) return;
    saving.value = true;
    const submitted = signature.value;
    try {
      const value = await updateEncounter(
        id,
        JSON.parse(submitted) as typeof form,
        record.value.revision,
      );
      record.value = value;
      savedSignature.value = submitted;
    } catch (cause) {
      serverConflict.value = isAxiosError(cause) && cause.response?.status === 409;
      error.value = getApiErrorMessage(
        cause,
        'Could not save. Your changes remain in this editor.',
      );
      autosync.value = false;
    } finally {
      saving.value = false;
    }
  };
  const persist = useDebounceFn(async () => {
    if (!loading.value && !locked.value && !id) await draft.persist();
    if (id && autosync.value && dirty.value && !locked.value) await save();
  }, 400);
  watch(signature, () => {
    void persist();
  });
  // Enabling autosync also saves changes already made, and a queued save resumes
  // after an in-flight operation without requiring another edit.
  watch([autosync, dirty, locked], () => {
    if (id && autosync.value && dirty.value && !locked.value) void persist();
  });
  const changeStatus = computed(() => {
    if (saving.value) return autosync.value ? 'Autosyncing' : 'Saving';
    if (publication.isCreating.value) return 'Creating';
    if (serverConflict.value) return 'Save conflict';
    if (id) return dirty.value ? (autosync.value ? 'Queued' : 'Unsaved') : 'Saved';
    if (draft.storageUnavailable.value) return 'Draft not saved';
    if (draft.conflict.value) return 'Draft conflict';
    return 'Local draft';
  });
  const selectBoss = async (item: GalleryItem | null) => {
    if (locked.value) return;
    const selection = ++bossSelection;
    if (!item) {
      form.boss_card_id = null;
      form.boss_group_id = null;
      factions.value = [];
      return;
    }
    const cardId = item.result_type === 'card_group' ? item.anchor_card_id : item.id;
    try {
      const card = await fetchCard<CardListItem>(cardId);
      if (selection !== bossSelection || locked.value) return;
      cards.value[card.id] = card;
      form.boss_card_id = card.id;
      form.boss_group_id = item.result_type === 'card_group' ? item.group_id : null;
      factions.value = [...(card.card_factions ?? [])];
    } catch (cause) {
      error.value = getApiErrorMessage(cause, 'Could not select boss.');
    }
  };
  const add = (item: GalleryItem) => {
    if (locked.value || item.result_type !== 'card' || item.card_pool !== 'evil') return;
    cards.value[item.id] = item;
    const entry = form.entries.find((value) => value.card_id === item.id);
    if (entry) entry.quantity += 1;
    else form.entries.push({ card_id: item.id, quantity: 1 });
  };
  const quantity = (cardId: string, value: number) => {
    if (locked.value || !Number.isInteger(value)) return;
    if (value <= 0) form.entries = form.entries.filter((entry) => entry.card_id !== cardId);
    else {
      const entry = form.entries.find((item) => item.card_id === cardId);
      if (entry) entry.quantity = value;
    }
  };
  const move = (index: number, direction: number) => {
    if (locked.value || index + direction < 0 || index + direction >= form.entries.length) return;
    const entries = [...form.entries];
    [entries[index], entries[index + direction]] = [entries[index + direction], entries[index]];
    form.entries = entries;
  };
  const setDetails = (
    values: Partial<
      Pick<
        typeof form,
        'name' | 'description_markup' | 'long_description_markup' | 'factions' | 'visibility'
      >
    >,
  ) => {
    if (!locked.value) Object.assign(form, values);
  };
  const setMode = (value: typeof mode.value) => {
    if (!locked.value) mode.value = value;
  };
  const canLeave = () => {
    if (publication.hasTerminalNavigationRetry.value || openingConfirmedRecord.value) return true;
    if (
      saving.value ||
      recoveryBusy.value ||
      publication.isCreating.value ||
      publication.isReconciling.value
    )
      return false;
    if (publication.isCreationUnknown.value && publication.attempt.value) {
      const attempt = publication.attempt.value;
      return draft.isCreateAttemptDurable(attempt.draftId, attempt);
    }
    return true;
  };
  onBeforeRouteLeave(async () => {
    if (!canLeave()) return false;
    if (publication.hasTerminalNavigationRetry.value || openingConfirmedRecord.value) return true;
    if (!id && !publication.isCreationUnknown.value) await draft.persist();
    if (
      (id && dirty.value) ||
      (!id && !draft.isCurrentContentDurable())
    ) {
      return window.confirm('Leave with unsaved changes?');
    }
    return true;
  });
  useEventListener(window, 'beforeunload', (event: BeforeUnloadEvent) => {
    if (!canLeave() || (id && dirty.value) || (!id && !draft.isCurrentContentDurable())) {
      event.preventDefault();
      event.returnValue = '';
    }
  });
  onMounted(async () => {
    try {
      minimum.value = (await fetchEncounterRules()).minimum_cards;
    } catch {
      /* Resilient metadata fallback. */
    }
    if (id) await reload();
    else {
      loading.value = false;
      savedSignature.value = signature.value;
    }
  });
  return {
    id,
    form,
    cards,
    record,
    mode,
    factions,
    loading,
    saving,
    error,
    locked,
    dirty,
    total,
    boss,
    issues,
    draft,
    publication,
    recover,
    loadConflict,
    openCreated,
    reload,
    save,
    selectBoss,
    add,
    quantity,
    move,
    setDetails,
    setMode,
    serverConflict,
    autosync,
    changeStatus,
    recoveryBusy,
    minimum,
  };
};
