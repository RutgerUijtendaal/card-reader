import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { computed, nextTick, ref } from 'vue';
import { api } from '@/api/client';
import { TEMPLATE_PREVIEW_STORAGE_KEY } from '@/modules/admin/composables/templatePreviewUtils';
import { useTemplatePreview } from '@/modules/admin/composables/useTemplatePreview';

vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockedGet = vi.mocked(api.get);

const relativeDefinitionJson = JSON.stringify({
  id: 'mtg-like-v1',
  version: 7,
  regions: [
    {
      region_id: 'top_bar',
      parser_type: 'name_mana_cost',
      cut_region: {
        unit: 'relative',
        x: 0.1,
        y: 0.2,
        w: 0.3,
        h: 0.4,
      },
      ocr_config: {},
    },
  ],
});

const absoluteDefinitionJson = JSON.stringify({
  id: 'mtg-like-v1',
  version: 7,
  regions: [
    {
      region_id: 'top_bar',
      parser_type: 'name_mana_cost',
      cut_region: {
        unit: 'absolute',
        x: 40,
        y: 50,
        w: 120,
        h: 60,
      },
      ocr_config: {},
    },
  ],
});

const flushDebounce = async (): Promise<void> => {
  await vi.advanceTimersByTimeAsync(300);
  await nextTick();
};

describe('useTemplatePreview', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    mockedGet.mockReset();
    mockedGet.mockImplementation(async (url) => {
      if (url === '/cards') {
        return {
          data: {
            count: 0,
            next_page: null,
            previous_page: null,
            page: 1,
            page_size: 8,
            results: [],
          },
        };
      }
      throw new Error(`Unhandled request: ${String(url)}`);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    vi.clearAllMocks();
  });

  test('valid JSON updates preview regions immediately', async () => {
    const definitionJson = ref(relativeDefinitionJson);
    const preview = useTemplatePreview({
      definitionJson,
      templateKey: computed(() => 'mtg-like-v1'),
    });

    await flushDebounce();

    expect(preview.previewRegions.value).toHaveLength(1);
    expect(preview.previewRegions.value[0].region_id).toBe('top_bar');
    expect(preview.previewWarning.value).toBeNull();
  });

  test('invalid JSON preserves the last valid overlay', async () => {
    const definitionJson = ref(relativeDefinitionJson);
    const preview = useTemplatePreview({
      definitionJson,
      templateKey: computed(() => 'mtg-like-v1'),
    });

    await flushDebounce();
    expect(preview.previewRegions.value).toHaveLength(1);

    definitionJson.value = '{';
    await nextTick();

    expect(preview.previewRegions.value).toHaveLength(1);
    expect(preview.previewWarning.value).not.toBeNull();
  });

  test('absolute regions require template dimensions and keep the last valid overlay', async () => {
    const definitionJson = ref(relativeDefinitionJson);
    const preview = useTemplatePreview({
      definitionJson,
      templateKey: computed(() => 'mtg-like-v1'),
    });

    await flushDebounce();
    const previousRegion = preview.previewRegions.value[0];

    definitionJson.value = absoluteDefinitionJson;
    await nextTick();

    expect(preview.previewRegions.value).toEqual([previousRegion]);
    expect(preview.previewWarning.value).toContain('card_width and card_height');
  });

  test('restores the persisted preview card when it is still fetchable', async () => {
    localStorage.setItem(
      TEMPLATE_PREVIEW_STORAGE_KEY,
      JSON.stringify({
        id: 'card-1',
        label: 'Card One',
        name: 'Card One',
        template_id: 'mtg-like-v1',
        image_url: '/cards/card-1/image',
        scope: 'current-template',
      }),
    );
    mockedGet.mockImplementation(async (url) => {
      if (url === '/cards/card-1') {
        return {
          data: {
            id: 'card-1',
            label: 'Card One',
            name: 'Card One',
            template_id: 'mtg-like-v1',
            image_url: '/cards/card-1/image',
          },
        };
      }
      if (url === '/cards') {
        return {
          data: {
            count: 0,
            next_page: null,
            previous_page: null,
            page: 1,
            page_size: 8,
            results: [],
          },
        };
      }
      throw new Error(`Unhandled request: ${String(url)}`);
    });

    const preview = useTemplatePreview({
      definitionJson: ref(relativeDefinitionJson),
      templateKey: computed(() => 'mtg-like-v1'),
    });

    await preview.restorePreviewCard();
    await nextTick();

    expect(preview.selectedPreviewCard.value?.id).toBe('card-1');
  });

  test('missing persisted preview card falls back cleanly', async () => {
    localStorage.setItem(
      TEMPLATE_PREVIEW_STORAGE_KEY,
      JSON.stringify({
        id: 'missing-card',
        label: 'Missing Card',
        name: 'Missing Card',
        template_id: 'mtg-like-v1',
        image_url: '/cards/missing-card/image',
        scope: 'current-template',
      }),
    );
    mockedGet.mockImplementation(async (url) => {
      if (url === '/cards/missing-card') {
        throw new Error('Not found');
      }
      if (url === '/cards') {
        return {
          data: {
            count: 0,
            next_page: null,
            previous_page: null,
            page: 1,
            page_size: 8,
            results: [],
          },
        };
      }
      throw new Error(`Unhandled request: ${String(url)}`);
    });

    const preview = useTemplatePreview({
      definitionJson: ref(relativeDefinitionJson),
      templateKey: computed(() => 'mtg-like-v1'),
    });

    await preview.restorePreviewCard();
    await nextTick();

    expect(preview.selectedPreviewCard.value).toBeNull();
    expect(localStorage.getItem(TEMPLATE_PREVIEW_STORAGE_KEY)).toBeNull();
  });

  test('search defaults to the current template scope when a template key is available', async () => {
    const definitionJson = ref(relativeDefinitionJson);
    useTemplatePreview({
      definitionJson,
      templateKey: computed(() => 'mtg-like-v1'),
    });

    await flushDebounce();

    expect(mockedGet).toHaveBeenCalledWith(
      '/cards',
      expect.objectContaining({
        params: expect.objectContaining({
          template_id: 'mtg-like-v1',
        }),
      }),
    );
  });
});
