export type ApiErrorMessageOptions = {
  includeErrorMessage?: boolean;
};

export const getApiErrorDetail = (error: unknown): string | null => {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return null;
  }

  const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof detail === 'string' && detail.trim().length > 0 ? detail : null;
};

export const getApiErrorMessage = (
  error: unknown,
  fallback: string,
  options: ApiErrorMessageOptions = {},
): string => {
  const detail = getApiErrorDetail(error);
  if (detail !== null) {
    return detail;
  }

  if (
    options.includeErrorMessage &&
    typeof error === 'object' &&
    error !== null &&
    'message' in error
  ) {
    return String((error as { message: unknown }).message);
  }

  return fallback;
};

export const getApiErrorMessageWithCause = (error: unknown, fallback: string): string =>
  getApiErrorMessage(error, fallback, { includeErrorMessage: true });
