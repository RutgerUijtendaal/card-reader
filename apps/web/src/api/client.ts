import axios from 'axios';

export const DEFAULT_API_BASE_URL = import.meta.env.DEV
  ? 'http://127.0.0.1:8000'
  : 'http://127.0.0.1:18600';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
});
