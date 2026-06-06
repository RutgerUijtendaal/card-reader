import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';
import { useDebounceFn, useLocalStorage } from '@vueuse/core';
import { api } from '@/api/client';
import { managementCardSearchLifecycleParams } from '@/composables/card-filters/cardLifecycle';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import type {
  TemplateDefinition,
  TemplatePreviewCardOption,
  TemplatePreviewRenderRegion,
  TemplatePreviewScope,
  TemplatePreviewSelectionState,
} from '@/modules/admin/types';
import {
  buildTemplatePreviewRenderRegions,
  normalizeTemplatePreviewCard,
  parseTemplatePreviewDefinition,
  TEMPLATE_PREVIEW_STORAGE_KEY,
} from '@/modules/admin/composables/templatePreviewUtils';

type TemplatePreviewCardDetail = {
  id: string;
  label: string;
  name: string;
  template_id: string;
  image_url: string | null;
};

type UseTemplatePreviewOptions = {
  definitionJson: Ref<string>;
  templateKey: ComputedRef<string>;
};

type TemplatePreviewSelectionStorage = Record<string, TemplatePreviewSelectionState>;

const UNSAVED_TEMPLATE_PREVIEW_STORAGE_KEY = '__unsaved-template__';

const toPreviewCardOption = (
  value: CardListItem | TemplatePreviewCardDetail,
): TemplatePreviewCardOption => ({
  id: value.id,
  label: value.label,
  name: value.name,
  template_id: value.template_id,
  image_url: value.image_url ?? null,
});

export const useTemplatePreview = ({ definitionJson, templateKey }: UseTemplatePreviewOptions) => {
  const previewSearchQuery = ref('');
  const previewScope = ref<TemplatePreviewScope>('current-template');
  const previewCards = ref<TemplatePreviewCardOption[]>([]);
  const selectedPreviewCard = ref<TemplatePreviewCardOption | null>(null);
  const previewLoading = ref(false);
  const previewWarning = ref<string | null>(null);
  const lastValidDefinition = ref<TemplateDefinition | null>(null);
  const lastValidRegions = ref<TemplatePreviewRenderRegion[]>([]);
  const hasInitializedSelection = ref(false);
  const isRestoringSelection = ref(false);
  let restoreRequestId = 0;
  let searchRequestId = 0;

  const storedSelections = useLocalStorage<TemplatePreviewSelectionStorage>(
    TEMPLATE_PREVIEW_STORAGE_KEY,
    {},
    {
      serializer: {
        read: (value) => {
          if (!value) return {};
          try {
            const parsed = JSON.parse(value) as unknown;
            if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
              return {};
            }

            const restored: TemplatePreviewSelectionStorage = {};
            for (const [key, rawSelection] of Object.entries(parsed)) {
              if (!key.trim() || !rawSelection || typeof rawSelection !== 'object' || Array.isArray(rawSelection)) {
                continue;
              }

              const parsedSelection = rawSelection as Partial<TemplatePreviewSelectionState>;
              const normalized = normalizeTemplatePreviewCard(parsedSelection);
              const scope = parsedSelection.scope === 'all-cards' ? 'all-cards' : 'current-template';
              if (normalized) {
                restored[key] = { ...normalized, scope };
              }
            }

            return restored;
          } catch {
            return {};
          }
        },
        write: (value) => JSON.stringify(value),
      },
    },
  );

  const templateScopedKey = computed(() => templateKey.value.trim());
  const selectionStorageKey = computed(() => templateScopedKey.value || UNSAVED_TEMPLATE_PREVIEW_STORAGE_KEY);
  const templateScopeAvailable = computed(() => templateScopedKey.value.length > 0);
  const defaultPreviewScope = computed<TemplatePreviewScope>(() =>
    templateScopeAvailable.value ? 'current-template' : 'all-cards',
  );
  const effectivePreviewScope = computed<TemplatePreviewScope>(() =>
    previewScope.value === 'current-template' && templateScopeAvailable.value ? 'current-template' : 'all-cards',
  );

  const activePreviewDefinition = computed(() => lastValidDefinition.value);
  const previewRegions = computed(() => lastValidRegions.value);
  const previewReady = computed(() => previewRegions.value.length > 0);

  const updatePreviewState = (): void => {
    const parsed = parseTemplatePreviewDefinition(definitionJson.value);
    if (!parsed.ok) {
      previewWarning.value = lastValidRegions.value.length > 0 ? parsed.message : `Preview unavailable: ${parsed.message}`;
      return;
    }

    const rendered = buildTemplatePreviewRenderRegions(parsed.definition);
    if (!rendered.ok) {
      previewWarning.value = lastValidRegions.value.length > 0 ? rendered.message : `Preview unavailable: ${rendered.message}`;
      return;
    }

    lastValidDefinition.value = parsed.definition;
    lastValidRegions.value = rendered.regions;
    previewWarning.value = null;
  };

  const setSelectedPreviewCard = (card: TemplatePreviewCardOption): void => {
    selectedPreviewCard.value = card;
  };

  const selectPreviewCard = (card: TemplatePreviewCardOption): void => {
    restoreRequestId += 1;
    setSelectedPreviewCard(card);
  };

  const setStoredSelection = (selection: TemplatePreviewSelectionState | null): void => {
    const key = selectionStorageKey.value;
    const next = { ...storedSelections.value };
    if (selection) {
      next[key] = selection;
    } else {
      delete next[key];
    }
    storedSelections.value = next;
  };

  const searchPreviewCards = async (expectedStorageKey = selectionStorageKey.value): Promise<void> => {
    const requestId = ++searchRequestId;
    previewLoading.value = true;
    try {
      const params: Record<string, string | number | boolean | undefined> = {
        ...managementCardSearchLifecycleParams(),
        page_size: 8,
        show_groups: false,
      };
      const query = previewSearchQuery.value.trim();
      if (query) {
        params.q = query;
      }
      if (effectivePreviewScope.value === 'current-template' && templateScopedKey.value) {
        params.template_id = templateScopedKey.value;
      }

      const response = await api.get<PaginatedCardsResponse<CardListItem>>('/cards', { params });
      if (requestId !== searchRequestId || expectedStorageKey !== selectionStorageKey.value) {
        return;
      }

      previewCards.value = response.data.results.filter((row) => row.result_type === 'card').map(toPreviewCardOption);

      if (!selectedPreviewCard.value && !previewSearchQuery.value.trim() && previewCards.value.length > 0) {
        setSelectedPreviewCard(previewCards.value[0]);
      }
    } finally {
      if (requestId === searchRequestId) {
        previewLoading.value = false;
      }
    }
  };

  const debouncedSearchPreviewCards = useDebounceFn(() => {
    void searchPreviewCards();
  }, 250);

  const restoreStoredPreviewCard = async (): Promise<void> => {
    const requestId = ++restoreRequestId;
    const storageKey = selectionStorageKey.value;
    const stored = storedSelections.value[storageKey] ?? null;
    isRestoringSelection.value = true;
    if (!stored) {
      previewScope.value = defaultPreviewScope.value;
      selectedPreviewCard.value = null;
      isRestoringSelection.value = false;
      await searchPreviewCards(storageKey);
      return;
    }

    previewScope.value = stored.scope;
    selectedPreviewCard.value = normalizeTemplatePreviewCard(stored);
    isRestoringSelection.value = false;

    try {
      const response = await api.get<TemplatePreviewCardDetail>(`/cards/${stored.id}`);
      if (requestId !== restoreRequestId || storageKey !== selectionStorageKey.value) {
        return;
      }
      const restored = toPreviewCardOption(response.data);
      selectedPreviewCard.value = restored;
      setStoredSelection({ ...restored, scope: previewScope.value });
    } catch {
      if (requestId !== restoreRequestId || storageKey !== selectionStorageKey.value) {
        return;
      }
      selectedPreviewCard.value = null;
      setStoredSelection(null);
    }

    await searchPreviewCards(storageKey);
  };

  const restorePreviewCard = async (): Promise<void> => {
    if (hasInitializedSelection.value) {
      return;
    }

    hasInitializedSelection.value = true;
    await restoreStoredPreviewCard();
  };

  watch(
    [definitionJson],
    () => {
      updatePreviewState();
    },
    { immediate: true },
  );

  watch(
    [previewSearchQuery, effectivePreviewScope, templateScopedKey],
    () => {
      debouncedSearchPreviewCards();
    },
    { immediate: true },
  );

  watch(previewScope, (value) => {
    if (value === 'current-template' && !templateScopeAvailable.value) {
      previewScope.value = 'all-cards';
    }
  });

  watch(
    selectedPreviewCard,
    (value) => {
      if (isRestoringSelection.value) {
        return;
      }
      setStoredSelection(value ? { ...value, scope: previewScope.value } : null);
    },
    { deep: true },
  );

  watch(previewScope, (value) => {
    if (isRestoringSelection.value) {
      return;
    }
    if (selectedPreviewCard.value) {
      setStoredSelection({ ...selectedPreviewCard.value, scope: value });
    }
  });

  watch(templateScopedKey, () => {
    if (!hasInitializedSelection.value) {
      return;
    }
    void restoreStoredPreviewCard();
  });

  return {
    activePreviewDefinition,
    previewCards,
    previewLoading,
    previewRegions,
    previewReady,
    previewScope,
    previewSearchQuery,
    previewWarning,
    restorePreviewCard,
    selectedPreviewCard,
    selectPreviewCard,
    templateScopeAvailable,
  };
};
