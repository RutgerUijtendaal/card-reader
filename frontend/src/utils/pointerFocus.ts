const FINE_POINTER_MEDIA_QUERY = '(hover: hover) and (pointer: fine)';

export const isFinePointerDevice = (): boolean =>
  typeof window !== 'undefined'
  && typeof window.matchMedia === 'function'
  && window.matchMedia(FINE_POINTER_MEDIA_QUERY).matches;

export const blurAfterFinePointerActivation = (event: Event): void => {
  if (!isFinePointerDevice() || !(event.currentTarget instanceof HTMLElement)) {
    return;
  }

  event.currentTarget.blur();
};
