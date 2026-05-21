import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';
import { useDebounceFn, useLocalStorage } from '@vueuse/core';
import { api } from '@/api/client';
import type { CardListItem, PaginatedCardsResponse } from '@/modules/card-detail/types';
import type {
  TemplateDefinition,
  TemplatePreviewCardOption,
  TemplatePreviewRenderRegion,
  TemplatePreviewScope,
  TemplatePreviewSelectionState,
} from '@/modules/settings/types';
import {
  buildTemplatePreviewRenderRegions,
  normalizeTemplatePreviewCard,
  parseTemplatePreviewDefinition,
  TEMPLATE_PREVIEW_STORAGE_KEY,
} from '@/modules/settings/composables/templatePreviewUtils';

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

  const storedSelection = useLocalStorage<TemplatePreviewSelectionState | null>(
    TEMPLATE_PREVIEW_STORAGE_KEY,
    null,
    {
      serializer: {
        read: (value) => {
          if (!value) return null;
          try {
            const parsed = JSON.parse(value) as Partial<TemplatePreviewSelectionState>;
            const normalized = normalizeTemplatePreviewCard(parsed);
            const scope = parsed.scope === 'all-cards' ? 'all-cards' : 'current-template';
            return normalized ? { ...normalized, scope } : null;
          } catch {
            return null;
          }
        },
        write: (value) => JSON.stringify(value),
      },
    },
  );

  const templateScopedKey = computed(() => templateKey.value.trim());
  const templateScopeAvailable = computed(() => templateScopedKey.value.length > 0);
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

  const selectPreviewCard = (card: TemplatePreviewCardOption): void => {
    selectedPreviewCard.value = card;
  };

  const searchPreviewCards = async (): Promise<void> => {
    previewLoading.value = true;
    try {
      const params: Record<string, string | number | boolean | undefined> = {
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
      previewCards.value = response.data.results.filter((row) => row.result_type === 'card').map(toPreviewCardOption);

      if (!selectedPreviewCard.value && !previewSearchQuery.value.trim() && previewCards.value.length > 0) {
        selectPreviewCard(previewCards.value[0]);
      }
    } finally {
      previewLoading.value = false;
    }
  };

  const debouncedSearchPreviewCards = useDebounceFn(() => {
    void searchPreviewCards();
  }, 250);

  const restorePreviewCard = async (): Promise<void> => {
    if (hasInitializedSelection.value) {
      return;
    }

    hasInitializedSelection.value = true;
    const stored = storedSelection.value;
    if (!stored) {
      await searchPreviewCards();
      return;
    }

    previewScope.value = stored.scope;
    selectedPreviewCard.value = normalizeTemplatePreviewCard(stored);

    try {
      const response = await api.get<TemplatePreviewCardDetail>(`/cards/${stored.id}`);
      const restored = toPreviewCardOption(response.data);
      selectedPreviewCard.value = restored;
      storedSelection.value = { ...restored, scope: previewScope.value };
    } catch {
      selectedPreviewCard.value = null;
      storedSelection.value = null;
    }

    await searchPreviewCards();
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
      storedSelection.value = value ? { ...value, scope: previewScope.value } : null;
    },
    { deep: true },
  );

  watch(previewScope, (value) => {
    if (selectedPreviewCard.value) {
      storedSelection.value = { ...selectedPreviewCard.value, scope: value };
    }
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
