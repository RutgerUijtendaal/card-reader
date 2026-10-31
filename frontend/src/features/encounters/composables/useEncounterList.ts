import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useDebounceFn } from '@vueuse/core';
import { fetchEncounters } from '@/domain/encounters/api';
import type { EncounterSummary } from '@/domain/encounters/types';
import { CARD_FACTION_OPTIONS } from '@/domain/cards/cardFactions';
import { getApiErrorMessage } from '@/shared/api/errors';

export const useEncounterList = () => {
  const route = useRoute();
  const router = useRouter();
  const staff = computed(() => route.path === '/staff/encounters');
  const query = ref('');
  const factions = ref<string[]>([]);
  const records = ref<EncounterSummary[]>([]);
  const count = ref(0);
  const nextPage = ref<number | null>(null);
  const loading = ref(true);
  const loadingMore = ref(false);
  const error = ref('');
  const moreError = ref('');
  let generation = 0;
  let disposed = false;
  const routeQuery = computed(() => {
    const raw = route.query.factions;
    const selected = Array.isArray(raw) ? raw : raw ? [raw] : [];
    return {
      q: typeof route.query.q === 'string' ? route.query.q : '',
      factions: CARD_FACTION_OPTIONS.filter((option) => selected.includes(option.value)).map(
        (option) => option.value,
      ),
    };
  });
  const filterQuery = computed(() => ({
    ...(routeQuery.value.q ? { q: routeQuery.value.q } : {}),
    ...(routeQuery.value.factions.length ? { factions: routeQuery.value.factions } : {}),
  }));
  const load = async (append = false) => {
    const page = append ? nextPage.value : 1;
    if (!page || (append && (loading.value || loadingMore.value))) return;
    const current = ++generation;
    if (append) {
      loadingMore.value = true;
      moreError.value = '';
    } else {
      loading.value = true;
      loadingMore.value = false;
      error.value = '';
      moreError.value = '';
    }
    const params = new URLSearchParams({
      q: routeQuery.value.q,
      page: String(page),
      page_size: '10',
    });
    routeQuery.value.factions.forEach((faction) => params.append('factions', faction));
    try {
      const result = await fetchEncounters(staff.value, params);
      if (current !== generation) return;
      const existing = new Set(records.value.map((record) => record.id));
      records.value = append
        ? [...records.value, ...result.results.filter((record) => !existing.has(record.id))]
        : result.results;
      count.value = result.count;
      nextPage.value = result.next_page;
    } catch (cause) {
      if (current === generation) {
        const message = getApiErrorMessage(cause, 'Could not load Encounters.');
        if (append) moreError.value = message;
        else error.value = message;
      }
    } finally {
      if (current === generation) {
        loading.value = false;
        loadingMore.value = false;
      }
    }
  };
  const updateRoute = useDebounceFn(() => {
    if (disposed) return;
    const selected = CARD_FACTION_OPTIONS.filter((option) =>
      factions.value.includes(option.value),
    ).map((option) => option.value);
    if (
      query.value === routeQuery.value.q &&
      JSON.stringify(selected) === JSON.stringify(routeQuery.value.factions)
    )
      return;
    void router.replace({
      path: route.path,
      query: {
        ...(query.value ? { q: query.value } : {}),
        ...(selected.length ? { factions: selected } : {}),
      },
    });
  }, 250);
  watch(
    [query, factions],
    () => {
      void updateRoute();
    },
    { deep: true },
  );
  watch(
    [() => route.path, routeQuery],
    () => {
      query.value = routeQuery.value.q;
      factions.value = [...routeQuery.value.factions];
      records.value = [];
      count.value = 0;
      nextPage.value = null;
      void load();
    },
    { immediate: true },
  );
  onBeforeUnmount(() => {
    disposed = true;
    generation++;
  });
  const reset = () => {
    query.value = '';
    factions.value = [];
  };
  const toggleFaction = (faction: string) => {
    factions.value = factions.value.includes(faction)
      ? factions.value.filter((value) => value !== faction)
      : [...factions.value, faction];
  };
  return {
    staff,
    query,
    factions,
    records,
    count,
    nextPage,
    loading,
    loadingMore,
    error,
    moreError,
    filterQuery,
    load,
    reset,
    toggleFaction,
  };
};
