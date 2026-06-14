export const MIDDLE_ZOOM_TARGET_WIDTH_REM = 19.5;
export const MIDDLE_ZOOM_VIEWPORT_MARGIN_PX = 12;

const clampCenterToViewport = (
  center: number,
  visualSize: number,
  viewportStart: number,
  viewportSize: number,
): number => {
  const minCenter = viewportStart + MIDDLE_ZOOM_VIEWPORT_MARGIN_PX + visualSize / 2;
  const maxCenter = viewportStart + viewportSize - MIDDLE_ZOOM_VIEWPORT_MARGIN_PX - visualSize / 2;
  if (minCenter > maxCenter) {
    return viewportStart + viewportSize / 2;
  }
  return Math.min(Math.max(center, minCenter), maxCenter);
};

export const getCardZoomOverlayStyle = (
  element: HTMLElement,
  tapped: boolean,
): Record<string, string> => {
  const rect = element.getBoundingClientRect();
  const layoutWidth = element.offsetWidth || rect.width || 1;
  const layoutHeight = element.offsetHeight || rect.height || layoutWidth * (88 / 63);
  const rootFontSize = Number.parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
  const targetSourceWidth = MIDDLE_ZOOM_TARGET_WIDTH_REM * rootFontSize;
  const targetSourceHeight = targetSourceWidth * (layoutHeight / layoutWidth);
  const viewport = window.visualViewport;
  const viewportLeft = viewport?.offsetLeft ?? 0;
  const viewportTop = viewport?.offsetTop ?? 0;
  const viewportWidth = viewport?.width ?? (window.innerWidth || document.documentElement.clientWidth);
  const viewportHeight = viewport?.height ?? (window.innerHeight || document.documentElement.clientHeight);
  const baseVisualWidth = tapped ? targetSourceHeight : targetSourceWidth;
  const baseVisualHeight = tapped ? targetSourceWidth : targetSourceHeight;
  const maxVisualWidth = Math.max(1, viewportWidth - MIDDLE_ZOOM_VIEWPORT_MARGIN_PX * 2);
  const maxVisualHeight = Math.max(1, viewportHeight - MIDDLE_ZOOM_VIEWPORT_MARGIN_PX * 2);
  const fitScale = Math.min(
    1,
    maxVisualWidth / baseVisualWidth,
    maxVisualHeight / baseVisualHeight,
  );
  const sourceWidth = targetSourceWidth * fitScale;
  const sourceHeight = targetSourceHeight * fitScale;
  const visualWidth = baseVisualWidth * fitScale;
  const visualHeight = baseVisualHeight * fitScale;
  const centerX = clampCenterToViewport(rect.left + rect.width / 2, visualWidth, viewportLeft, viewportWidth);
  const centerY = clampCenterToViewport(rect.top + rect.height / 2, visualHeight, viewportTop, viewportHeight);

  return {
    '--playtest-zoom-source-height': `${sourceHeight}px`,
    '--playtest-zoom-source-width': `${sourceWidth}px`,
    height: `${visualHeight}px`,
    left: `${centerX - visualWidth / 2}px`,
    top: `${centerY - visualHeight / 2}px`,
    width: `${visualWidth}px`,
  };
};
