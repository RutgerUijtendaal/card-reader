import axios from 'axios';

const defaultApiBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return `http://${window.location.hostname}:8000`;
  }

  const { protocol, origin } = window.location;
  if (protocol === 'http:' || protocol === 'https:') {
    return origin;
  }
  return origin;
};

export const DEFAULT_API_BASE_URL = defaultApiBaseUrl();

export const toAbsoluteApiUrl = (urlPath: string): string => {
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }

  const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});
