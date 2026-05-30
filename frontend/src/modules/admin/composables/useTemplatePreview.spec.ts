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

const createDeferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((innerResolve, innerReject) => {
    resolve = innerResolve;
    reject = innerReject;
  });
  return { promise, reject, resolve };
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
        'mtg-like-v1': {
          id: 'card-1',
          label: 'Card One',
          name: 'Card One',
          template_id: 'mtg-like-v1',
          image_url: '/cards/card-1/image',
          scope: 'current-template',
        },
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
        'mtg-like-v1': {
          id: 'missing-card',
          label: 'Missing Card',
          name: 'Missing Card',
          template_id: 'mtg-like-v1',
          image_url: '/cards/missing-card/image',
          scope: 'current-template',
        },
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
    expect(localStorage.getItem(TEMPLATE_PREVIEW_STORAGE_KEY)).toBe('{}');
  });

  test('restores a separate persisted preview card when switching templates', async () => {
    localStorage.setItem(
      TEMPLATE_PREVIEW_STORAGE_KEY,
      JSON.stringify({
        'mtg-like-v1': {
          id: 'card-1',
          label: 'Card One',
          name: 'Card One',
          template_id: 'mtg-like-v1',
          image_url: '/cards/card-1/image',
          scope: 'current-template',
        },
        'mtg-like-v2': {
          id: 'card-2',
          label: 'Card Two',
          name: 'Card Two',
          template_id: 'mtg-like-v2',
          image_url: '/cards/card-2/image',
          scope: 'all-cards',
        },
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
      if (url === '/cards/card-2') {
        return {
          data: {
            id: 'card-2',
            label: 'Card Two',
            name: 'Card Two',
            template_id: 'mtg-like-v2',
            image_url: '/cards/card-2/image',
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

    const templateKey = ref('mtg-like-v1');
    const preview = useTemplatePreview({
      definitionJson: ref(relativeDefinitionJson),
      templateKey: computed(() => templateKey.value),
    });

    await preview.restorePreviewCard();
    await nextTick();
    expect(preview.selectedPreviewCard.value?.id).toBe('card-1');
    expect(preview.previewScope.value).toBe('current-template');

    templateKey.value = 'mtg-like-v2';
    await nextTick();
    await vi.runOnlyPendingTimersAsync();
    await nextTick();

    expect(preview.selectedPreviewCard.value?.id).toBe('card-2');
    expect(preview.previewScope.value).toBe('all-cards');
  });

  test('resets to current template scope when switching to a template without a saved preview card', async () => {
    localStorage.setItem(
      TEMPLATE_PREVIEW_STORAGE_KEY,
      JSON.stringify({
        'mtg-like-v1': {
          id: 'card-1',
          label: 'Card One',
          name: 'Card One',
          template_id: 'mtg-like-v1',
          image_url: '/cards/card-1/image',
          scope: 'all-cards',
        },
      }),
    );
    mockedGet.mockImplementation(async (url, config) => {
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
        const params = config && typeof config === 'object' && 'params' in config ? config.params : {};
        const results =
          params && typeof params === 'object' && 'template_id' in params && params.template_id === 'mtg-like-v2'
            ? []
            : [
                {
                  id: 'unrelated-card',
                  label: 'Unrelated Card',
                  name: 'Unrelated Card',
                  template_id: 'other-template',
                  image_url: '/cards/unrelated-card/image',
                  result_type: 'card',
                },
              ];
        return {
          data: {
            count: results.length,
            next_page: null,
            previous_page: null,
            page: 1,
            page_size: 8,
            results,
          },
        };
      }
      throw new Error(`Unhandled request: ${String(url)}`);
    });

    const templateKey = ref('mtg-like-v1');
    const preview = useTemplatePreview({
      definitionJson: ref(relativeDefinitionJson),
      templateKey: computed(() => templateKey.value),
    });

    await preview.restorePreviewCard();
    await nextTick();
    expect(preview.previewScope.value).toBe('all-cards');

    templateKey.value = 'mtg-like-v2';
    await nextTick();
    await vi.runOnlyPendingTimersAsync();
    await nextTick();

    expect(preview.previewScope.value).toBe('current-template');
    expect(preview.selectedPreviewCard.value).toBeNull();
    expect(localStorage.getItem(TEMPLATE_PREVIEW_STORAGE_KEY)).not.toContain('unrelated-card');
  });

  test('ignores restore-triggered search results after switching templates again', async () => {
    type CardsResponse = Awaited<ReturnType<typeof api.get>>;
    const firstTemplateSearch = createDeferred<CardsResponse>();
    const secondTemplateSearch = createDeferred<CardsResponse>();

    mockedGet.mockImplementation((async (url, config) => {
      if (url === '/cards') {
        const params = config && typeof config === 'object' && 'params' in config ? config.params : {};
        if (params && typeof params === 'object' && 'template_id' in params && params.template_id === 'mtg-like-v1') {
          return firstTemplateSearch.promise;
        }
        if (params && typeof params === 'object' && 'template_id' in params && params.template_id === 'mtg-like-v2') {
          return secondTemplateSearch.promise;
        }
      }
      throw new Error(`Unhandled request: ${String(url)}`);
    }) as typeof api.get);

    const templateKey = ref('mtg-like-v1');
    const preview = useTemplatePreview({
      definitionJson: ref(relativeDefinitionJson),
      templateKey: computed(() => templateKey.value),
    });

    const restoreFirstTemplate = preview.restorePreviewCard();
    await nextTick();

    templateKey.value = 'mtg-like-v2';
    await nextTick();

    firstTemplateSearch.resolve({
      data: {
        count: 1,
        next_page: null,
        previous_page: null,
        page: 1,
        page_size: 8,
        results: [
          {
            id: 'stale-card',
            label: 'Stale Card',
            name: 'Stale Card',
            template_id: 'mtg-like-v1',
            image_url: '/cards/stale-card/image',
            result_type: 'card',
          },
        ],
      },
    } as CardsResponse);
    await restoreFirstTemplate;
    await nextTick();

    expect(preview.selectedPreviewCard.value).toBeNull();
    expect(localStorage.getItem(TEMPLATE_PREVIEW_STORAGE_KEY)).not.toContain('stale-card');

    secondTemplateSearch.resolve({
      data: {
        count: 0,
        next_page: null,
        previous_page: null,
        page: 1,
        page_size: 8,
        results: [],
      },
    } as CardsResponse);
    await vi.runOnlyPendingTimersAsync();
    await nextTick();

    expect(preview.selectedPreviewCard.value).toBeNull();
  });

  test('manual preview card selection cancels a pending saved-card restore', async () => {
    type CardResponse = Awaited<ReturnType<typeof api.get>>;
    const savedCardDetail = createDeferred<CardResponse>();

    localStorage.setItem(
      TEMPLATE_PREVIEW_STORAGE_KEY,
      JSON.stringify({
        'mtg-like-v1': {
          id: 'card-1',
          label: 'Card One',
          name: 'Card One',
          template_id: 'mtg-like-v1',
          image_url: '/cards/card-1/image',
          scope: 'current-template',
        },
      }),
    );
    mockedGet.mockImplementation((async (url) => {
      if (url === '/cards/card-1') {
        return savedCardDetail.promise;
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
    }) as typeof api.get);

    const preview = useTemplatePreview({
      definitionJson: ref(relativeDefinitionJson),
      templateKey: computed(() => 'mtg-like-v1'),
    });

    const restore = preview.restorePreviewCard();
    await nextTick();
    preview.selectPreviewCard({
      id: 'card-2',
      label: 'Card Two',
      name: 'Card Two',
      template_id: 'mtg-like-v1',
      image_url: '/cards/card-2/image',
    });

    savedCardDetail.resolve({
      data: {
        id: 'card-1',
        label: 'Card One',
        name: 'Card One',
        template_id: 'mtg-like-v1',
        image_url: '/cards/card-1/image',
      },
    } as CardResponse);
    await restore;
    await nextTick();

    expect(preview.selectedPreviewCard.value?.id).toBe('card-2');
    expect(localStorage.getItem(TEMPLATE_PREVIEW_STORAGE_KEY)).toContain('card-2');
    expect(localStorage.getItem(TEMPLATE_PREVIEW_STORAGE_KEY)).not.toContain('"id":"card-1"');
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
