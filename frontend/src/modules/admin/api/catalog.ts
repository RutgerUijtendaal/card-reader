import { api } from '@/api/client';
import type {
  CatalogApiResponse,
  CatalogKind,
  CatalogResponse,
  DeckTagCatalogApiResponse,
  DeckTagRecord,
  DeckTagUpsertRequest,
  KeywordUpsertRequest,
  KnownCatalogKind,
  KeywordRecord,
  SuggestionAcceptExistingRequest,
  SuggestionAcceptNewRequest,
  SuggestionRecord,
  SymbolRecord,
  SymbolAssetUploadResponse,
  SymbolUpsertRequest,
  TagRecord,
  TagUpsertRequest,
  TypeRecord,
  TypeUpsertRequest,
} from '@/modules/admin/types';
import {
  isKnownCatalogKind,
  normalizeCatalogResponse,
} from '@/modules/admin/composables/catalogAdminUtils';

const createPathByKind: Record<KnownCatalogKind, string> = {
  keywords: '/admin/keywords',
  tags: '/admin/tags',
  symbols: '/admin/symbols',
  types: '/admin/types',
  'deck-roles': '/admin/deck-tags',
  'deck-types': '/admin/deck-tags',
};

const pathForKindAndId = (kind: KnownCatalogKind, id: string): string =>
  `${createPathByKind[kind]}/${id}`;

export const fetchCatalog = async (): Promise<CatalogResponse> => {
  const response = await api.get<CatalogApiResponse>('/admin/catalog');
  return normalizeCatalogResponse(response.data);
};

export const fetchDeckTagCatalog = async (): Promise<{
  roles: DeckTagRecord[];
  types: DeckTagRecord[];
  suggestedTypes: SuggestionRecord[];
}> => {
  const response = await api.get<DeckTagCatalogApiResponse>('/admin/deck-tags');
  const normalizeTag = (tag: DeckTagCatalogApiResponse['roles'][number]): DeckTagRecord => ({
    ...tag,
    identifiers: [],
    identifiers_text: '',
  });
  return {
    roles: response.data.roles.map(normalizeTag),
    types: response.data.types.map(normalizeTag),
    suggestedTypes: response.data.suggested_types.map((suggestion) => ({
      ...suggestion,
      label: suggestion.display_value,
      key: suggestion.normalized_value,
      occurrences: [],
      linked_decks: suggestion.linked_decks ?? [],
    })),
  };
};

export const createCatalogEntry = async (
  kind: CatalogKind,
  payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest | DeckTagUpsertRequest,
): Promise<void> => {
  if (!isKnownCatalogKind(kind)) {
    throw new Error('Suggestions cannot be created via the catalog CRUD API.');
  }
  await api.post(createPathByKind[kind], payload);
};

export const updateCatalogEntry = async (
  kind: CatalogKind,
  id: string,
  payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest | DeckTagUpsertRequest,
): Promise<void> => {
  if (!isKnownCatalogKind(kind)) {
    throw new Error('Suggestions cannot be updated via the catalog CRUD API.');
  }
  await api.patch(pathForKindAndId(kind, id), payload);
};

export const deleteCatalogEntry = async (kind: CatalogKind, id: string): Promise<void> => {
  if (!isKnownCatalogKind(kind)) {
    throw new Error('Suggestions cannot be deleted via the catalog CRUD API.');
  }
  await api.delete(pathForKindAndId(kind, id));
};

export const fetchKnownCatalogEntryDetail = async (
  kind: KnownCatalogKind,
  id: string,
): Promise<KeywordRecord | TagRecord | TypeRecord | SymbolRecord | DeckTagRecord> => {
  const response = await api.get<KeywordRecord | TagRecord | TypeRecord | SymbolRecord | DeckTagRecord>(pathForKindAndId(kind, id));
  return response.data;
};

const suggestionBasePath = (kind: CatalogKind): string => {
  if (kind === 'suggested-deck-types') return '/admin/deck-tag-suggestions';
  return `/admin/suggestions/${kind === 'suggested-tags' ? 'tag' : 'type'}`;
};

export const fetchSuggestionDetail = async (
  kind: CatalogKind,
  id: string,
): Promise<SuggestionRecord> => {
  const response = await api.get<SuggestionRecord>(`${suggestionBasePath(kind)}/${id}`);
  return response.data;
};

export const acceptSuggestionToExisting = async (
  kind: CatalogKind,
  id: string,
  payload: SuggestionAcceptExistingRequest,
): Promise<void> => {
  await api.post(`${suggestionBasePath(kind)}/${id}/accept`, payload);
};

export const acceptSuggestionAsNew = async (
  kind: CatalogKind,
  id: string,
  payload: SuggestionAcceptNewRequest,
): Promise<void> => {
  await api.post(`${suggestionBasePath(kind)}/${id}/accept`, payload);
};

export const rejectSuggestion = async (kind: CatalogKind, id: string): Promise<void> => {
  await api.post(`${suggestionBasePath(kind)}/${id}/reject`);
};

export const reopenSuggestion = async (kind: CatalogKind, id: string): Promise<void> => {
  if (kind !== 'suggested-deck-types') {
    throw new Error('Only deck tag suggestions can be reopened.');
  }
  await api.post(`${suggestionBasePath(kind)}/${id}/reopen`);
};

export const uploadSymbolAsset = async (file: File): Promise<SymbolAssetUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<SymbolAssetUploadResponse>(
    '/admin/symbols/assets/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  );
  return response.data;
};
