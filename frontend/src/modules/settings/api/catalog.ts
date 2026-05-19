import { api } from '@/api/client';
import type {
  CatalogApiResponse,
  CatalogKind,
  CatalogResponse,
  KeywordUpsertRequest,
  KnownCatalogKind,
  KeywordRecord,
  SuggestionAcceptExistingRequest,
  SuggestionAcceptNewRequest,
  SuggestionKind,
  SuggestionRecord,
  SymbolRecord,
  SymbolAssetUploadResponse,
  SymbolUpsertRequest,
  TagRecord,
  TagUpsertRequest,
  TypeRecord,
  TypeUpsertRequest,
} from '@/modules/settings/types';
import {
  isKnownCatalogKind,
  normalizeCatalogResponse,
} from '@/modules/settings/composables/catalogSettingsUtils';

const createPathByKind: Record<KnownCatalogKind, string> = {
  keywords: '/settings/keywords',
  tags: '/settings/tags',
  symbols: '/settings/symbols',
  types: '/settings/types',
};

const pathForKindAndId = (kind: KnownCatalogKind, id: string): string =>
  `${createPathByKind[kind]}/${id}`;

export const fetchCatalog = async (): Promise<CatalogResponse> => {
  const response = await api.get<CatalogApiResponse>('/settings/catalog');
  return normalizeCatalogResponse(response.data);
};

export const createCatalogEntry = async (
  kind: CatalogKind,
  payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest,
): Promise<void> => {
  if (!isKnownCatalogKind(kind)) {
    throw new Error('Suggestions cannot be created via the catalog CRUD API.');
  }
  await api.post(createPathByKind[kind], payload);
};

export const updateCatalogEntry = async (
  kind: CatalogKind,
  id: string,
  payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest,
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
): Promise<KeywordRecord | TagRecord | TypeRecord | SymbolRecord> => {
  const response = await api.get<KeywordRecord | TagRecord | TypeRecord | SymbolRecord>(pathForKindAndId(kind, id));
  return response.data;
};

export const fetchSuggestionDetail = async (
  kind: SuggestionKind,
  id: string,
): Promise<SuggestionRecord> => {
  const response = await api.get<SuggestionRecord>(`/settings/suggestions/${kind}/${id}`);
  return response.data;
};

export const acceptSuggestionToExisting = async (
  kind: SuggestionKind,
  id: string,
  payload: SuggestionAcceptExistingRequest,
): Promise<void> => {
  await api.post(`/settings/suggestions/${kind}/${id}/accept`, payload);
};

export const acceptSuggestionAsNew = async (
  kind: SuggestionKind,
  id: string,
  payload: SuggestionAcceptNewRequest,
): Promise<void> => {
  await api.post(`/settings/suggestions/${kind}/${id}/accept`, payload);
};

export const rejectSuggestion = async (kind: SuggestionKind, id: string): Promise<void> => {
  await api.post(`/settings/suggestions/${kind}/${id}/reject`);
};

export const uploadSymbolAsset = async (file: File): Promise<SymbolAssetUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<SymbolAssetUploadResponse>(
    '/settings/symbols/assets/upload',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  );
  return response.data;
};
