import { createApp, defineComponent, h } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { fetchOperationsOverview } from '@/features/operations/api';
import { useOperationsOverview } from '@/features/operations/composables/useOperationsOverview';
import type { OperationsOverview } from '@/features/operations/types';

vi.mock('@/features/operations/api', () => ({
  fetchOperationsOverview: vi.fn(),
}));

const mockedFetchOperationsOverview = vi.mocked(fetchOperationsOverview);

const createDeferred = <T,>() => {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((innerResolve) => {
    resolve = innerResolve;
  });
  return { promise, resolve };
};

const buildOverview = (generatedAt: string): OperationsOverview => ({
  generated_at: generatedAt,
  stale_after_seconds: 30,
  workers: [],
  queues: [],
});

describe('useOperationsOverview', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  test('ignores stale responses and preserves the latest refresh state', async () => {
    const staleRequest = createDeferred<OperationsOverview>();
    const latestRequest = createDeferred<OperationsOverview>();
    mockedFetchOperationsOverview
      .mockReturnValueOnce(staleRequest.promise)
      .mockReturnValueOnce(latestRequest.promise);

    let state!: ReturnType<typeof useOperationsOverview>;
    const app = createApp(
      defineComponent({
        setup() {
          state = useOperationsOverview();
          return () => h('div');
        },
      }),
    );
    const host = document.createElement('div');
    app.mount(host);
    const latestLoad = state.loadOverview();

    staleRequest.resolve(buildOverview('stale'));
    await staleRequest.promise;
    await Promise.resolve();

    expect(state.overview.value).toBeNull();
    expect(state.refreshing.value).toBe(true);

    latestRequest.resolve(buildOverview('latest'));
    await latestLoad;

    expect(state.overview.value?.generated_at).toBe('latest');
    expect(state.loading.value).toBe(false);
    expect(state.refreshing.value).toBe(false);

    app.unmount();
  });
});
