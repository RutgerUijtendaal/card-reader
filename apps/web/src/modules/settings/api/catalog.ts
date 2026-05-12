import { api } from '@/api/client';
import type {
  CatalogApiResponse,
  CatalogKind,
  CatalogResponse,
  KeywordUpsertRequest,
  SymbolAssetUploadResponse,
  SymbolUpsertRequest,
  TagUpsertRequest,
  TypeUpsertRequest,
} from '@/modules/settings/types';
import { normalizeCatalogResponse } from '@/modules/settings/composables/catalogSettingsUtils';

const createPathByKind: Record<CatalogKind, string> = {
  keywords: '/settings/keywords',
  tags: '/settings/tags',
  symbols: '/settings/symbols',
  types: '/settings/types',
};

const pathForKindAndId = (kind: CatalogKind, id: string): string =>
  `${createPathByKind[kind]}/${id}`;

export const fetchCatalog = async (): Promise<CatalogResponse> => {
  const response = await api.get<CatalogApiResponse>('/settings/catalog');
  return normalizeCatalogResponse(response.data);
};

export const createCatalogEntry = async (
  kind: CatalogKind,
  payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest,
): Promise<void> => {
  await api.post(createPathByKind[kind], payload);
};

export const updateCatalogEntry = async (
  kind: CatalogKind,
  id: string,
  payload: KeywordUpsertRequest | TagUpsertRequest | TypeUpsertRequest | SymbolUpsertRequest,
): Promise<void> => {
  await api.patch(pathForKindAndId(kind, id), payload);
};

export const deleteCatalogEntry = async (kind: CatalogKind, id: string): Promise<void> => {
  await api.delete(pathForKindAndId(kind, id));
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
