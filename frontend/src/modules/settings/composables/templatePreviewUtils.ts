import type {
  JsonObject,
  RegionBounds,
  TemplateDefinition,
  TemplatePreviewCardOption,
  TemplatePreviewRenderRegion,
  TemplateRegionDefinition,
} from '@/modules/settings/types';

export const TEMPLATE_PREVIEW_STORAGE_KEY = 'card-reader.template-preview';

type PreviewParseSuccess = {
  ok: true;
  definition: TemplateDefinition;
};

type PreviewParseFailure = {
  ok: false;
  message: string;
};

type PreviewRegionBuildSuccess = {
  ok: true;
  regions: TemplatePreviewRenderRegion[];
};

type PreviewRegionBuildFailure = {
  ok: false;
  message: string;
};

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value);

const isPreviewableBounds = (value: unknown): value is RegionBounds => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const candidate = value as Partial<RegionBounds>;
  return (
    (candidate.unit === 'relative' || candidate.unit === 'absolute') &&
    isFiniteNumber(candidate.x) &&
    isFiniteNumber(candidate.y) &&
    isFiniteNumber(candidate.w) &&
    isFiniteNumber(candidate.h)
  );
};

const isPreviewableRegion = (value: unknown): value is TemplateRegionDefinition => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }

  const candidate = value as Partial<TemplateRegionDefinition>;
  return typeof candidate.region_id === 'string' && candidate.region_id.trim().length > 0 && isPreviewableBounds(candidate.cut_region);
};

const asTemplateDefinition = (value: JsonObject): TemplateDefinition => {
  return value as TemplateDefinition;
};

export const parseTemplatePreviewDefinition = (
  rawJson: string,
): PreviewParseSuccess | PreviewParseFailure => {
  const trimmed = rawJson.trim();
  if (!trimmed) {
    return { ok: false, message: 'Definition JSON is empty.' };
  }

  try {
    const parsed = JSON.parse(trimmed);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      return { ok: false, message: 'Definition JSON must be an object.' };
    }

    const definition = asTemplateDefinition(parsed as JsonObject);
    if (!Array.isArray(definition.regions)) {
      return { ok: false, message: 'Preview requires a regions array.' };
    }

    return {
      ok: true,
      definition,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Definition JSON must be valid JSON.';
    return {
      ok: false,
      message,
    };
  }
};

const toRelativeRegion = (
  region: TemplateRegionDefinition,
  cardWidth: number | undefined,
  cardHeight: number | undefined,
): TemplatePreviewRenderRegion | null => {
  const bounds = region.cut_region;
  if (bounds.unit === 'relative') {
    return {
      region_id: region.region_id,
      parser_type: region.parser_type,
      left_pct: bounds.x * 100,
      top_pct: bounds.y * 100,
      width_pct: bounds.w * 100,
      height_pct: bounds.h * 100,
    };
  }

  if (!cardWidth || !cardHeight || cardWidth <= 0 || cardHeight <= 0) {
    return null;
  }

  return {
    region_id: region.region_id,
    parser_type: region.parser_type,
    left_pct: (bounds.x / cardWidth) * 100,
    top_pct: (bounds.y / cardHeight) * 100,
    width_pct: (bounds.w / cardWidth) * 100,
    height_pct: (bounds.h / cardHeight) * 100,
  };
};

export const buildTemplatePreviewRenderRegions = (
  definition: TemplateDefinition,
): PreviewRegionBuildSuccess | PreviewRegionBuildFailure => {
  const regions = Array.isArray(definition.regions) ? definition.regions.filter(isPreviewableRegion) : [];
  if (regions.length === 0) {
    return {
      ok: false,
      message: 'Preview requires at least one region with region_id and valid cut_region coordinates.',
    };
  }

  const hasAbsoluteRegion = regions.some((region) => region.cut_region.unit === 'absolute');
  const cardWidth = typeof definition.card_width === 'number' ? definition.card_width : undefined;
  const cardHeight = typeof definition.card_height === 'number' ? definition.card_height : undefined;
  if (hasAbsoluteRegion && (!cardWidth || !cardHeight)) {
    return {
      ok: false,
      message: 'Absolute preview regions require card_width and card_height on the template definition.',
    };
  }

  const renderedRegions = regions
    .map((region) => toRelativeRegion(region, cardWidth, cardHeight))
    .filter((region): region is TemplatePreviewRenderRegion => region !== null)
    .filter(
      (region) =>
        Number.isFinite(region.left_pct) &&
        Number.isFinite(region.top_pct) &&
        Number.isFinite(region.width_pct) &&
        Number.isFinite(region.height_pct),
    );

  if (renderedRegions.length === 0) {
    return {
      ok: false,
      message: 'Preview could not render any valid regions from the current JSON.',
    };
  }

  return {
    ok: true,
    regions: renderedRegions,
  };
};

export const normalizeTemplatePreviewCard = (
  value: Partial<TemplatePreviewCardOption> | null | undefined,
): TemplatePreviewCardOption | null => {
  if (!value) {
    return null;
  }

  if (
    typeof value.id !== 'string' ||
    typeof value.label !== 'string' ||
    typeof value.name !== 'string' ||
    typeof value.template_id !== 'string'
  ) {
    return null;
  }

  return {
    id: value.id,
    label: value.label,
    name: value.name,
    template_id: value.template_id,
    image_url: typeof value.image_url === 'string' ? value.image_url : null,
  };
};
