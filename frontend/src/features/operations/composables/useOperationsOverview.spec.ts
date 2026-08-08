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

let mountedState!: ReturnType<typeof useOperationsOverview>;
const TestOperationsOverview = defineComponent({
  setup() {
    mountedState = useOperationsOverview();
    return () => h('div');
  },
});

const mountOperationsOverview = () => {
  const app = createApp(TestOperationsOverview);
  const host = document.createElement('div');
  app.mount(host);
  return { app, state: mountedState };
};

describe('useOperationsOverview', () => {
  afterEach(() => {
    vi.useRealTimers();
    mockedFetchOperationsOverview.mockReset();
  });

  test('ignores stale responses and preserves the latest refresh state', async () => {
    const staleRequest = createDeferred<OperationsOverview>();
    const latestRequest = createDeferred<OperationsOverview>();
    mockedFetchOperationsOverview
      .mockReturnValueOnce(staleRequest.promise)
      .mockReturnValueOnce(latestRequest.promise);

    const { app, state } = mountOperationsOverview();
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

  test('does not replace a slow request on the polling interval', async () => {
    vi.useFakeTimers();
    const slowRequest = createDeferred<OperationsOverview>();
    mockedFetchOperationsOverview
      .mockReturnValueOnce(slowRequest.promise)
      .mockResolvedValueOnce(buildOverview('polled'));

    const { app, state } = mountOperationsOverview();

    await vi.advanceTimersByTimeAsync(15_000);

    expect(mockedFetchOperationsOverview).toHaveBeenCalledTimes(1);
    expect(state.loading.value).toBe(true);

    slowRequest.resolve(buildOverview('slow'));
    await slowRequest.promise;
    await Promise.resolve();

    expect(state.overview.value?.generated_at).toBe('slow');
    expect(state.loading.value).toBe(false);

    await vi.advanceTimersByTimeAsync(5_000);

    expect(mockedFetchOperationsOverview).toHaveBeenCalledTimes(2);
    expect(state.overview.value?.generated_at).toBe('polled');

    app.unmount();
  });
});
