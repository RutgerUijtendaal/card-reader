import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { buildCardReturnLocation, getCardReturnLabel } from '@/domain/card-navigation/cardReturnState';
import { fetchCard, fetchCardFilters, fetchCardVersions } from '@/domain/cards/api';
import { buildEffectiveSymbolIds, getRuleTextSymbolState } from '@/domain/cards/utils/cards/ruleTextSymbols';
import {
  ACTIVE_CARD_LIFECYCLE_STATUS,
  normalizeCardLifecycleStatus,
} from '@/domain/cards/utils/filters/cardLifecycle';
import { useGalleryCardNavigation } from '@/domain/cards/utils/gallery/galleryNavigation';
import type {
  CardFiltersResponse,
  CardGroupSummary,
  CardVersionDetail,
  FieldSourceValue,
  MetadataGroupName,
  MetadataOption,
  ScalarFieldName,
  SymbolFilterOption,
  SymbolLookupMap,
} from '@/domain/cards/types';
import type { CardPool } from '@/domain/cards/cardPools';
import type {
  CardDetail,
  EditorForm,
  MetadataSearchState,
  ReparseTemplateOption,
} from '@/features/card-detail/types';
import { metadataGroups, scalarFields } from '@/features/card-detail/types';
import { formatCardDetailDate } from '@/features/card-detail/utils/cardDetailFormatters';
import { fetchTemplates } from '@/domain/templates/api';
import { fetchDeckRulesMetadata } from '@/domain/decks/api';
import {
  fallbackDeckBuildingDefaultConfig,
  fallbackDeckBuildingConfigExample,
  formatDeckBuildingConfigJson,
} from '@/domain/decks/utils/deckRules';
import { queryString } from '@/shared/router/routeState';
import { getApiErrorMessage } from '@/shared/api/errors';
import {
  patchLatestCardVersion,
  promoteCardVersion,
  queueCardReparse,
} from '@/features/card-detail/api';

export const useCardDetailState = () => {
  const route = useRoute();
  const router = useRouter();
  const card = ref<CardDetail | null>(null);
  const versions = ref<CardVersionDetail[]>([]);
  const selectedVersionId = ref<string>('');
  const filterOptions = ref<CardFiltersResponse>({ keywords: [], tags: [], symbols: [], types: [] });
  const symbolByKey = ref<SymbolLookupMap>({});
  const reparseTemplates = ref<ReparseTemplateOption[]>([]);
  const deckBuildingConfigExample = ref(formatDeckBuildingConfigJson(fallbackDeckBuildingConfigExample));
  const reparseTemplateId = ref('');
  const galleryNavigation = useGalleryCardNavigation(route, router, 'edit');
  const isLoadingInitial = ref(true);
  const isSaving = ref(false);
  const isQueuingReparse = ref(false);
  const promotingVersionId = ref<string | null>(null);
  const saveMessage = ref('');
  const saveError = ref('');
  let loadRequestId = 0;

  const form = reactive<EditorForm>({
    name: '',
    type_line: '',
    mana_cost: '',
    attack: '',
    health: '',
    rules_text: '',
    card_pool: 'player',
    card_roles: [],
    card_factions: [],
    card_mana_families: [],
    deck_building_config: formatDeckBuildingConfigJson(fallbackDeckBuildingDefaultConfig),
    lifecycle_status: ACTIVE_CARD_LIFECYCLE_STATUS,
    keyword_ids: [],
    tag_ids: [],
    type_ids: [],
    additional_symbol_ids: [],
  });
  const metadataSearch = reactive<MetadataSearchState>({
    keywords: '',
    tags: '',
    types: '',
    symbols: '',
  });

  const selectedVersion = computed<CardVersionDetail | null>(
    () => versions.value.find((version) => version.version_id === selectedVersionId.value) ?? null,
  );

  const metadataOptionsById = computed<Record<string, MetadataOption | SymbolFilterOption>>(() =>
    Object.fromEntries(
      [
        ...(filterOptions.value.keywords ?? []),
        ...(filterOptions.value.tags ?? []),
        ...(filterOptions.value.types ?? []),
        ...(filterOptions.value.symbols ?? []),
      ].map((row) => [row.id, row]),
    ),
  );
  const symbolOptionsById = computed<Record<string, SymbolFilterOption>>(() =>
    Object.fromEntries((filterOptions.value.symbols ?? []).map((row) => [row.id, row])),
  );
  const ruleTextSymbolState = computed(() =>
    getRuleTextSymbolState(form.rules_text, filterOptions.value.symbols ?? []),
  );
  const effectiveSymbolIds = computed(() =>
    buildEffectiveSymbolIds(ruleTextSymbolState.value.referencedSymbolIds, form.additional_symbol_ids),
  );
  const ruleTextUnknownSymbolKeys = computed(() => ruleTextSymbolState.value.unknownKeys);
  const rulesTextSymbols = computed<SymbolFilterOption[]>(() =>
    ruleTextSymbolState.value.referencedSymbolIds
      .map((id) => symbolOptionsById.value[id])
      .filter((symbol): symbol is SymbolFilterOption => Boolean(symbol)),
  );
  const additionalSymbols = computed<SymbolFilterOption[]>(() =>
    form.additional_symbol_ids
      .map((id) => symbolOptionsById.value[id])
      .filter(
        (symbol): symbol is SymbolFilterOption =>
          Boolean(symbol) && !ruleTextSymbolState.value.referencedSymbolIds.includes(symbol.id),
      ),
  );

  const isBusy = computed(() => isSaving.value || isQueuingReparse.value || promotingVersionId.value !== null);
  const backButtonLabel = computed(() => `Back to ${getCardReturnLabel(route.query)}`);
  const reviewFocusPropertyKey = computed(() => queryString(route.query.property_key));

  const goBack = (): void => {
    void router.push(buildCardReturnLocation(route.query));
  };

  const loadCard = async (): Promise<void> => {
    const requestId = ++loadRequestId;
    const cardId = String(route.params.id);
    isLoadingInitial.value = true;
    try {
      const [cardResponse, versionsResponse, filtersResponse, templates, deckRulesMetadata] = await Promise.all([
        fetchCard<CardDetail>(cardId),
        fetchCardVersions(cardId),
        fetchCardFilters(),
        fetchTemplates(),
        fetchDeckRulesMetadata().catch(() => null),
      ]);

      if (requestId !== loadRequestId) {
        return;
      }

      card.value = cardResponse;
      versions.value = versionsResponse;
      filterOptions.value = filtersResponse;
      symbolByKey.value = Object.fromEntries(
        (filtersResponse.symbols ?? []).map((row) => [row.key, row]),
      );
      reparseTemplates.value = templates.map((row) => ({
        id: row.id,
        key: row.key,
        label: row.label,
      }));
      if (deckRulesMetadata) {
        deckBuildingConfigExample.value = formatDeckBuildingConfigJson(deckRulesMetadata.example_config);
      }
      const queryVersionId = queryString(route.query.version_id);
      selectedVersionId.value =
        versions.value.find((version) => version.version_id === queryVersionId)?.version_id ??
        versions.value.find((version) => version.is_latest)?.version_id ??
        versions.value[0]?.version_id ??
        '';
      saveMessage.value = '';
      saveError.value = '';
    } finally {
      if (requestId === loadRequestId) {
        isLoadingInitial.value = false;
      }
    }
  };

  const syncFormFromSelectedVersion = (): void => {
    const version = selectedVersion.value;
    if (!version) return;
    form.name = version.name ?? '';
    form.type_line = version.type_line ?? '';
    form.mana_cost = version.mana_cost ?? '';
    form.attack = version.attack === null ? '' : String(version.attack);
    form.health = version.health === null ? '' : String(version.health);
    form.rules_text = version.rules_text_enriched ?? version.rules_text ?? '';
    form.card_pool = version.card_pool;
    form.card_roles = [...version.card_roles];
    form.card_factions = [...(version.card_factions ?? [])];
    form.card_mana_families = [...(version.card_mana_families ?? [])];
    form.deck_building_config = formatDeckBuildingConfigJson(
      Object.keys(version.deck_building_config ?? {}).length > 0
        ? version.deck_building_config
        : fallbackDeckBuildingDefaultConfig,
    );
    form.lifecycle_status = normalizeCardLifecycleStatus(version.lifecycle_status);
    form.keyword_ids = [...version.keyword_ids];
    form.tag_ids = [...version.tag_ids];
    form.type_ids = [...version.type_ids];
    form.additional_symbol_ids = uniqueIds(version.symbol_ids);
    reparseTemplateId.value = version.template_id;
    saveMessage.value = '';
    saveError.value = '';
  };

  const selectVersion = (versionId: string): void => {
    selectedVersionId.value = versionId;
  };

  const applyUpdatedVersion = (updated: CardVersionDetail): boolean => {
    const previousVersion = versions.value.find((version) => version.version_id === updated.version_id);
    const poolChanged = previousVersion?.card_pool !== updated.card_pool;
    versions.value = synchronizeCardClassification(versions.value, updated);
    if (card.value) {
      card.value = {
        ...card.value,
        name: updated.name,
        label: updated.name,
        lifecycle_status: updated.lifecycle_status,
        card_groups: poolChanged
          ? reconcileCardGroupsAfterPoolChange(card.value.card_groups, updated.card_pool)
          : card.value.card_groups,
      };
    }
    selectedVersionId.value = updated.version_id;
    syncFormFromSelectedVersion();
    return poolChanged;
  };

  const patchLatestVersion = async (
    payload: Record<string, unknown>,
    successMessage = 'Version updated.',
  ): Promise<boolean> => {
    const version = selectedVersion.value;
    if (!version?.editable) return false;
    isSaving.value = true;
    saveMessage.value = '';
    saveError.value = '';
    try {
      const updatedVersion = await patchLatestCardVersion(version.id, payload);
      const poolChanged = applyUpdatedVersion(updatedVersion);
      if (poolChanged) {
        try {
          const refreshedCard = await fetchCard<CardDetail>(updatedVersion.id);
          if (card.value?.id === refreshedCard.id) {
            card.value = refreshedCard;
          }
        } catch (error) {
          console.error('Refresh card groups after pool change failed', error);
        }
      }
      saveMessage.value = successMessage;
      return true;
    } catch (error) {
      saveError.value = cardSaveErrorMessage(error);
      return false;
    } finally {
      isSaving.value = false;
    }
  };

  const saveVersionEdits = async (): Promise<void> => {
    const version = selectedVersion.value;
    if (!version?.editable) return;
    saveMessage.value = '';
    saveError.value = '';
    const selectedTemplateId = reparseTemplateId.value;
    const templateChanged = selectedTemplateId !== version.template_id;
    const updates = buildVersionUpdatePayload(form, version, effectiveSymbolIds.value);
    if (Object.keys(updates).length === 0 && templateChanged) {
      await queueLatestCardReparseForTemplate(selectedTemplateId);
      return;
    }
    if (Object.keys(updates).length === 0) {
      saveMessage.value = 'No changes to save.';
      return;
    }
    const saved = await patchLatestVersion(
      updates,
      'Changes saved. Edited fields and metadata are now locked to manual ownership.',
    );
    if (saved && templateChanged) {
      await queueLatestCardReparseForTemplate(selectedTemplateId);
    }
  };

  const saveCardEdits = async (): Promise<void> => {
    const version = selectedVersion.value;
    if (!version?.editable) return;
    saveMessage.value = '';
    saveError.value = '';
    let updates: Record<string, unknown>;
    try {
      updates = buildCardUpdatePayload(form, version);
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : 'Deck-building config must be valid JSON.';
      return;
    }
    if (Object.keys(updates).length === 0) {
      saveMessage.value = 'No card changes to save.';
      return;
    }
    await patchLatestVersion(updates, 'Card settings saved.');
  };

  const restoreField = async (fieldName: ScalarFieldName): Promise<void> => {
    await patchLatestVersion({ restore_fields: [fieldName] });
  };

  const unlockField = async (fieldName: ScalarFieldName): Promise<void> => {
    await patchLatestVersion({ unlock_fields: [fieldName] });
  };

  const restoreMetadataGroup = async (groupName: MetadataGroupName): Promise<void> => {
    await patchLatestVersion({ restore_metadata_groups: [groupName] });
  };

  const unlockMetadataGroup = async (groupName: MetadataGroupName): Promise<void> => {
    await patchLatestVersion({ unlock_metadata_groups: [groupName] });
  };

  const resetWholeCardToAuto = async (): Promise<void> => {
    await patchLatestVersion(
      {
        restore_fields: scalarFields.map((field) => field.name),
        restore_metadata_groups: metadataGroups.map((group) => group.name),
      },
      'Whole card reset to parsed values and auto ownership.',
    );
  };

  const queueLatestCardReparse = async (): Promise<void> => {
    await queueLatestCardReparseForTemplate(reparseTemplateId.value);
  };

  const queueLatestCardReparseForTemplate = async (templateId: string): Promise<void> => {
    const version = selectedVersion.value;
    if (!version?.editable) return;
    isQueuingReparse.value = true;
    saveMessage.value = '';
    saveError.value = '';
    try {
      saveMessage.value = await queueCardReparse(version.id, templateId);
    } finally {
      isQueuingReparse.value = false;
    }
  };

  const promoteVersion = async (versionId: string): Promise<void> => {
    const targetCard = card.value;
    const version = versions.value.find((item) => item.version_id === versionId);
    if (!targetCard || !version || version.is_latest || promotingVersionId.value !== null) {
      return;
    }

    promotingVersionId.value = versionId;
    saveMessage.value = '';
    saveError.value = '';
    try {
      const promotedVersion = await promoteCardVersion(targetCard.id, versionId);
      versions.value = versions.value.map((item) =>
        item.version_id === promotedVersion.version_id
          ? promotedVersion
          : { ...item, is_latest: false, editable: false },
      );
      card.value = {
        ...targetCard,
        label: promotedVersion.label,
        name: promotedVersion.name,
      };
      selectedVersionId.value = promotedVersion.version_id;
      syncFormFromSelectedVersion();
      saveMessage.value = 'Promoted printing to latest version.';
    } finally {
      promotingVersionId.value = null;
    }
  };

  const fieldSource = (fieldName: ScalarFieldName): FieldSourceValue =>
    selectedVersion.value?.field_sources.fields[fieldName] ?? 'auto';

  const metadataSource = (groupName: MetadataGroupName): FieldSourceValue =>
    selectedVersion.value?.field_sources.metadata[groupName] ?? 'auto';

  const fieldSourceLabel = (fieldName: ScalarFieldName): string =>
    fieldSource(fieldName) === 'manual' ? 'Manual' : 'Auto';

  const metadataSourceLabel = (groupName: MetadataGroupName): string =>
    metadataSource(groupName) === 'manual' ? 'Manual' : 'Auto';

  const fieldHasParsedSuggestion = (fieldName: ScalarFieldName): boolean => {
    const version = selectedVersion.value;
    if (!version?.editable) return false;
    return normalizeFieldValue(version, fieldName) !== normalizeParsedFieldValue(version, fieldName);
  };

  const formatParsedFieldValue = (fieldName: ScalarFieldName): string => {
    const version = selectedVersion.value;
    if (!version) return '';
    const value = version.parsed_snapshot.fields[fieldName];
    return value === null || value === '' ? 'Empty' : String(value);
  };

  const metadataHasParsedSuggestion = (groupName: MetadataGroupName): boolean => {
    const version = selectedVersion.value;
    if (!version?.editable) return false;
    return JSON.stringify(sortedIds(selectedIdsFromVersion(version, groupName, effectiveSymbolIds.value))) !== JSON.stringify(sortedIds(parsedIds(groupName, version)));
  };

  const selectedIds = (groupName: MetadataGroupName): string[] => {
    if (groupName === 'keywords') return form.keyword_ids;
    if (groupName === 'tags') return form.tag_ids;
    if (groupName === 'types') return form.type_ids;
    return effectiveSymbolIds.value;
  };

  const parsedMetadataLabels = (groupName: MetadataGroupName): string[] =>
    parsedIds(groupName, selectedVersion.value)
      .map((id) => metadataOptionsById.value[id]?.label ?? id)
      .sort((a, b) => a.localeCompare(b));

  const optionsForGroup = (groupName: MetadataGroupName): Array<MetadataOption | SymbolFilterOption> => {
    const options =
      groupName === 'keywords'
        ? (filterOptions.value.keywords ?? [])
        : groupName === 'tags'
          ? (filterOptions.value.tags ?? [])
          : groupName === 'types'
            ? (filterOptions.value.types ?? [])
            : (filterOptions.value.symbols ?? []);
    return filterMetadataOptions(options, metadataSearch[groupName]);
  };

  const setMetadataSearch = (groupName: MetadataGroupName, value: string): void => {
    metadataSearch[groupName] = value;
  };

  const toggleMetadataSelection = (groupName: MetadataGroupName, id: string, checked: boolean): void => {
    const target = selectedIds(groupName);
    const next = checked ? [...target, id] : target.filter((item) => item !== id);
    if (groupName === 'keywords') form.keyword_ids = next;
    else if (groupName === 'tags') form.tag_ids = next;
    else if (groupName === 'types') form.type_ids = next;
    else form.additional_symbol_ids = next.filter((item) => !ruleTextSymbolState.value.referencedSymbolIds.includes(item));
  };

  const toggleAdditionalSymbol = (id: string, checked: boolean): void => {
    const next = checked
      ? [...form.additional_symbol_ids, id]
      : form.additional_symbol_ids.filter((item) => item !== id);
    form.additional_symbol_ids = uniqueIds(next);
  };

  watch(() => route.params.id, loadCard);
  watch(selectedVersion, syncFormFromSelectedVersion, { immediate: true });

  return {
    route,
    card,
    versions,
    selectedVersionId,
    filterOptions,
    symbolByKey,
    hasGalleryContext: galleryNavigation.hasGalleryContext,
    previousCardId: galleryNavigation.previousCardId,
    nextCardId: galleryNavigation.nextCardId,
    hasMoreResults: galleryNavigation.hasMoreResults,
    isLoadingMoreCards: galleryNavigation.isLoadingMoreCards,
    positionLabel: galleryNavigation.positionLabel,
    reparseTemplates,
    reparseTemplateId,
    isSaving,
    isLoadingInitial,
    isQueuingReparse,
    promotingVersionId,
    saveMessage,
    saveError,
    deckBuildingConfigExample,
    form,
    metadataSearch,
    selectedVersion,
    isBusy,
    ruleTextUnknownSymbolKeys,
    rulesTextSymbols,
    additionalSymbols,
    effectiveSymbolIds,
    backButtonLabel,
    reviewFocusPropertyKey,
    goBack,
    goToPreviousCard: galleryNavigation.goToPreviousCard,
    goToNextCard: () => {
      void galleryNavigation.goToNextCard();
    },
    loadCard,
    selectVersion,
    saveCardEdits,
    saveVersionEdits,
    restoreField,
    unlockField,
    restoreMetadataGroup,
    unlockMetadataGroup,
    resetWholeCardToAuto,
    queueLatestCardReparse,
    promoteVersion,
    fieldSource,
    metadataSource,
    fieldSourceLabel,
    metadataSourceLabel,
    fieldHasParsedSuggestion,
    formatParsedFieldValue,
    metadataHasParsedSuggestion,
    selectedIds,
    parsedMetadataLabels,
    optionsForGroup,
    setMetadataSearch,
    toggleMetadataSelection,
    toggleAdditionalSymbol,
    toAbsoluteApiUrl,
    formatDate: formatCardDetailDate,
  };
};

export const cardSaveErrorMessage = (error: unknown): string => {
  const message = getApiErrorMessage(error, 'Card changes could not be saved.');
  if (!message.toLowerCase().includes('conflict')) {
    return message;
  }
  return `${message} Merge the duplicate cards before changing this card's name, pool, or factions.`;
};

const normalizeFieldValue = (version: CardVersionDetail, fieldName: ScalarFieldName): string => {
  if (fieldName === 'rules_text') {
    return String(version.rules_text_enriched ?? '');
  }
  if (fieldName === 'attack' || fieldName === 'health') {
    return String(version[fieldName] ?? '');
  }
  return String(version[fieldName] ?? '');
};

const normalizeParsedFieldValue = (version: CardVersionDetail, fieldName: ScalarFieldName): string => {
  const value = version.parsed_snapshot.fields[fieldName];
  return String(value ?? '');
};

const selectedIdsFromVersion = (
  version: CardVersionDetail,
  groupName: MetadataGroupName,
  effectiveSymbolIds: string[],
): string[] => {
  if (groupName === 'keywords') return version.keyword_ids;
  if (groupName === 'tags') return version.tag_ids;
  if (groupName === 'types') return version.type_ids;
  return effectiveSymbolIds;
};

const parsedIds = (groupName: MetadataGroupName, selectedVersion?: CardVersionDetail | null): string[] => {
  if (!selectedVersion) return [];
  if (groupName === 'keywords') return selectedVersion.parsed_snapshot.metadata.keyword_ids;
  if (groupName === 'tags') return selectedVersion.parsed_snapshot.metadata.tag_ids;
  if (groupName === 'types') return selectedVersion.parsed_snapshot.metadata.type_ids;
  return selectedVersion.parsed_snapshot.metadata.symbol_ids;
};

const sortedIds = (ids: string[]): string[] => [...ids].sort((a, b) => a.localeCompare(b));

const buildCardUpdatePayload = (
  form: EditorForm,
  version: CardVersionDetail,
): Record<string, unknown> => {
  const updates: Record<string, unknown> = {};

  if (form.card_pool !== version.card_pool) {
    updates.card_pool = form.card_pool;
  }
  if (JSON.stringify([...form.card_roles].sort()) !== JSON.stringify([...version.card_roles].sort())) {
    updates.card_roles = form.card_roles;
  }
  if (
    JSON.stringify([...form.card_factions].sort())
    !== JSON.stringify([...(version.card_factions ?? [])].sort())
  ) {
    updates.card_factions = form.card_factions;
  }
  if (
    JSON.stringify([...form.card_mana_families].sort())
    !== JSON.stringify([...(version.card_mana_families ?? [])].sort())
  ) {
    updates.card_mana_families = form.card_mana_families;
  }
  const deckBuildingConfig = parseJsonObject(form.deck_building_config);
  if (JSON.stringify(deckBuildingConfig) !== JSON.stringify(version.deck_building_config ?? {})) {
    updates.deck_building_config = deckBuildingConfig;
  }
  if (form.lifecycle_status !== normalizeCardLifecycleStatus(version.lifecycle_status)) {
    updates.lifecycle_status = form.lifecycle_status;
  }

  return updates;
};

const buildVersionUpdatePayload = (
  form: EditorForm,
  version: CardVersionDetail,
  effectiveSymbolIds: string[],
): Record<string, unknown> => {
  const updates: Record<string, unknown> = {};

  for (const fieldName of ['name', 'type_line', 'mana_cost', 'attack', 'health', 'rules_text'] as const) {
    if (normalizeFormFieldValue(form, fieldName) !== normalizeFieldValue(version, fieldName)) {
      updates[fieldName === 'rules_text' ? 'rules_text_enriched' : fieldName] = form[fieldName];
    }
  }

  if (!sameIds(form.keyword_ids, version.keyword_ids)) {
    updates.keyword_ids = form.keyword_ids;
  }
  if (!sameIds(form.tag_ids, version.tag_ids)) {
    updates.tag_ids = form.tag_ids;
  }
  if (!sameIds(form.type_ids, version.type_ids)) {
    updates.type_ids = form.type_ids;
  }
  if (!sameIds(effectiveSymbolIds, version.symbol_ids)) {
    updates.symbol_ids = effectiveSymbolIds;
  }

  return updates;
};

const normalizeFormFieldValue = (form: EditorForm, fieldName: ScalarFieldName): string =>
  String(form[fieldName] ?? '');

const sameIds = (left: string[], right: string[]): boolean =>
  JSON.stringify(sortedIds(left)) === JSON.stringify(sortedIds(right));

const uniqueIds = (ids: string[]): string[] => Array.from(new Set(ids));

export const reconcileCardGroupsAfterPoolChange = (
  groups: CardGroupSummary[],
  cardPool: CardPool,
): CardGroupSummary[] => groups.map((group) =>
  group.is_anchor ? { ...group, card_pool: cardPool } : group,
);

export type CardClassificationFields = Pick<
  CardVersionDetail,
  | 'version_id'
  | 'card_pool'
  | 'card_roles'
  | 'card_factions'
  | 'card_mana_families'
  | 'deck_building_config'
  | 'lifecycle_status'
>;

export const synchronizeCardClassification = <T extends CardClassificationFields>(
  versions: T[],
  updated: T,
): T[] =>
  versions.map((version) =>
    version.version_id === updated.version_id
      ? updated
      : {
          ...version,
          card_pool: updated.card_pool,
          card_roles: [...updated.card_roles],
          card_factions: [...(updated.card_factions ?? [])],
          card_mana_families: [...(updated.card_mana_families ?? [])],
          deck_building_config: updated.deck_building_config,
          lifecycle_status: updated.lifecycle_status,
        },
  );

const parseJsonObject = (value: string): Record<string, unknown> => {
  const parsed = JSON.parse(value.trim() || '{}') as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Deck-building config must be a JSON object.');
  }
  return parsed as Record<string, unknown>;
};

const filterMetadataOptions = <T extends MetadataOption | SymbolFilterOption>(
  options: T[],
  query: string,
): T[] => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return options;
  }

  return options.filter((option) => {
    const haystacks = [option.label, option.key];
    if ('text_token' in option) {
      haystacks.push(option.text_token);
    }
    return haystacks.some((value) => value.toLowerCase().includes(normalizedQuery));
  });
};
