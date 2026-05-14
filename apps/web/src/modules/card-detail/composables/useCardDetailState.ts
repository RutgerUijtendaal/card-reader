import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, DEFAULT_API_BASE_URL } from '@/api/client';
import type {
  CardDetail,
  CardFiltersResponse,
  CardVersionDetail,
  EditorForm,
  FieldSourceValue,
  MetadataGroupName,
  MetadataOption,
  MetadataSearchState,
  ScalarFieldName,
  SymbolFilterOption,
  SymbolLookupMap,
} from '@/modules/card-detail/types';
import { metadataGroups, scalarFields } from '@/modules/card-detail/types';

export const useCardDetailState = () => {
  const route = useRoute();
  const router = useRouter();
  const card = ref<CardDetail | null>(null);
  const versions = ref<CardVersionDetail[]>([]);
  const selectedVersionId = ref<string>('');
  const filterOptions = ref<CardFiltersResponse>({ keywords: [], tags: [], symbols: [], types: [] });
  const symbolByKey = ref<SymbolLookupMap>({});
  const isSaving = ref(false);
  const isQueuingReparse = ref(false);
  const saveMessage = ref('');

  const form = reactive<EditorForm>({
    name: '',
    type_line: '',
    mana_cost: '',
    attack: '',
    health: '',
    rules_text: '',
    keyword_ids: [],
    tag_ids: [],
    type_ids: [],
    symbol_ids: [],
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

  const isBusy = computed(() => isSaving.value || isQueuingReparse.value);

  const goBack = (): void => {
    if (window.history.length > 1) {
      router.back();
      return;
    }
    void router.push(`/cards/${route.params.id}`);
  };

  const loadCard = async (): Promise<void> => {
    const cardId = String(route.params.id);
    const [cardResponse, versionsResponse, filtersResponse] = await Promise.all([
      api.get<CardDetail>(`/cards/${cardId}`),
      api.get<CardVersionDetail[]>(`/cards/${cardId}/generations`),
      api.get<CardFiltersResponse>('/cards/filters'),
    ]);

    card.value = cardResponse.data;
    versions.value = versionsResponse.data;
    filterOptions.value = filtersResponse.data;
    symbolByKey.value = Object.fromEntries(
      (filtersResponse.data.symbols ?? []).map((row) => [row.key, row]),
    );
    selectedVersionId.value =
      versions.value.find((version) => version.is_latest)?.version_id ??
      versions.value[0]?.version_id ??
      '';
    saveMessage.value = '';
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
    form.keyword_ids = [...version.keyword_ids];
    form.tag_ids = [...version.tag_ids];
    form.type_ids = [...version.type_ids];
    form.symbol_ids = [...version.symbol_ids];
    saveMessage.value = '';
  };

  const selectVersion = (versionId: string): void => {
    selectedVersionId.value = versionId;
  };

  const applyUpdatedVersion = (updated: CardVersionDetail): void => {
    versions.value = versions.value.map((version) =>
      version.version_id === updated.version_id ? updated : version,
    );
    if (card.value) {
      card.value = { ...card.value, name: updated.name, label: updated.name };
    }
    selectedVersionId.value = updated.version_id;
    syncFormFromSelectedVersion();
  };

  const patchLatestVersion = async (payload: Record<string, unknown>, successMessage = 'Version updated.'): Promise<void> => {
    const version = selectedVersion.value;
    if (!version?.editable) return;
    isSaving.value = true;
    saveMessage.value = '';
    try {
      const response = await api.patch<CardVersionDetail>(`/cards/${version.id}/latest-version`, payload);
      applyUpdatedVersion(response.data);
      saveMessage.value = successMessage;
    } finally {
      isSaving.value = false;
    }
  };

  const saveEdits = async (): Promise<void> => {
    const version = selectedVersion.value;
    if (!version?.editable) return;
    const updates = buildManualUpdatePayload(form, version);
    if (Object.keys(updates).length === 0) {
      saveMessage.value = 'No changes to save.';
      return;
    }
    await patchLatestVersion(
      updates,
      'Changes saved. Edited fields and metadata are now locked to manual ownership.',
    );
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
    const version = selectedVersion.value;
    if (!version?.editable) return;
    isQueuingReparse.value = true;
    saveMessage.value = '';
    try {
      const response = await api.post<{ message: string }>(`/cards/${version.id}/reparse`);
      saveMessage.value = response.data.message;
    } finally {
      isQueuingReparse.value = false;
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
    return JSON.stringify(sortedIds(selectedIdsFromVersion(version, groupName))) !== JSON.stringify(sortedIds(parsedIds(groupName, version)));
  };

  const selectedIds = (groupName: MetadataGroupName): string[] => {
    if (groupName === 'keywords') return form.keyword_ids;
    if (groupName === 'tags') return form.tag_ids;
    if (groupName === 'types') return form.type_ids;
    return form.symbol_ids;
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
    else form.symbol_ids = next;
  };

  const toAbsoluteApiUrl = (urlPath: string): string => {
    const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
    if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
      return urlPath;
    }
    return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
  };

  const formatDate = (value: string): string => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleDateString();
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
    isSaving,
    isQueuingReparse,
    saveMessage,
    form,
    metadataSearch,
    selectedVersion,
    isBusy,
    goBack,
    loadCard,
    selectVersion,
    saveEdits,
    restoreField,
    unlockField,
    restoreMetadataGroup,
    unlockMetadataGroup,
    resetWholeCardToAuto,
    queueLatestCardReparse,
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
    toAbsoluteApiUrl,
    formatDate,
  };
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

const selectedIdsFromVersion = (version: CardVersionDetail, groupName: MetadataGroupName): string[] => {
  if (groupName === 'keywords') return version.keyword_ids;
  if (groupName === 'tags') return version.tag_ids;
  if (groupName === 'types') return version.type_ids;
  return version.symbol_ids;
};

const parsedIds = (groupName: MetadataGroupName, selectedVersion?: CardVersionDetail | null): string[] => {
  if (!selectedVersion) return [];
  if (groupName === 'keywords') return selectedVersion.parsed_snapshot.metadata.keyword_ids;
  if (groupName === 'tags') return selectedVersion.parsed_snapshot.metadata.tag_ids;
  if (groupName === 'types') return selectedVersion.parsed_snapshot.metadata.type_ids;
  return selectedVersion.parsed_snapshot.metadata.symbol_ids;
};

const sortedIds = (ids: string[]): string[] => [...ids].sort((a, b) => a.localeCompare(b));

const buildManualUpdatePayload = (
  form: EditorForm,
  version: CardVersionDetail,
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
  if (!sameIds(form.symbol_ids, version.symbol_ids)) {
    updates.symbol_ids = form.symbol_ids;
  }

  return updates;
};

const normalizeFormFieldValue = (form: EditorForm, fieldName: ScalarFieldName): string =>
  String(form[fieldName] ?? '');

const sameIds = (left: string[], right: string[]): boolean =>
  JSON.stringify(sortedIds(left)) === JSON.stringify(sortedIds(right));

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
