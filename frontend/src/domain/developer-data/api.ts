import { api, toAbsoluteApiUrl } from '@/shared/api/client';
import type {
  DeveloperDataBuild,
  DeveloperDataBuildList,
  DeveloperDataCurrent,
  DeveloperDataGrant,
} from './types';

export const fetchCurrentDeveloperData = async (): Promise<DeveloperDataCurrent> => {
  const response = await api.get<DeveloperDataCurrent>('/developer-data/current');
  return response.data;
};

export const createDeveloperDataGrant = async (): Promise<DeveloperDataGrant> => {
  const response = await api.post<DeveloperDataGrant>('/developer-data/grants');
  return response.data;
};

export const developerDataDownloadUrl = (downloadUrl: string): string =>
  toAbsoluteApiUrl(downloadUrl);

export const fetchDeveloperDataBuilds = async (): Promise<DeveloperDataBuild[]> => {
  const response = await api.get<DeveloperDataBuildList>('/developer-data/builds');
  return response.data.builds;
};

export const createDeveloperDataBuild = async (): Promise<DeveloperDataBuild> => {
  const response = await api.post<DeveloperDataBuild>('/developer-data/builds');
  return response.data;
};

export const developerDataLockUrl = (downloadUrl: string): string =>
  toAbsoluteApiUrl(downloadUrl);
