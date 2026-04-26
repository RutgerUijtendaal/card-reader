import axios from 'axios';

const defaultApiBaseUrl = (): string => {
  if (import.meta.env.DEV) {
    return `http://${window.location.hostname}:8000`;
  }
  return 'http://127.0.0.1:18600';
};

export const DEFAULT_API_BASE_URL = defaultApiBaseUrl();

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
});
