import { createApp, defineComponent, h, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { fetchOperationsQueuePage } from '@/domain/operations/api';
import type { OperationsQueuePage } from '@/domain/operations/types';
import { useOperationsQueueHistory } from '@/features/operations/composables/useOperationsQueueHistory';

vi.mock('@/domain/operations/api', () => ({
  fetchOperationsQueuePage: vi.fn(),
}));

const mockedFetchOperationsQueuePage = vi.mocked(fetchOperationsQueuePage);
const emptyPage = (page: number): OperationsQueuePage => ({
  count: 0,
  next_page: null,
  previous_page: page > 1 ? page - 1 : null,
  page,
  page_size: 20,
  results: [],
});

describe('useOperationsQueueHistory', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test('polls the latest page but leaves older pages stable', async () => {
    vi.useFakeTimers();
    mockedFetchOperationsQueuePage.mockImplementation(async (_queueKey, page) => emptyPage(page));
    const queueKey = ref<string | null>('imports');
    const pageNumber = ref(2);
    let state!: ReturnType<typeof useOperationsQueueHistory>;
    const component = defineComponent({
      setup() {
        state = useOperationsQueueHistory(queueKey, pageNumber);
        return () => h('div');
      },
    });
    const app = createApp(component);
    app.mount(document.createElement('div'));

    await vi.waitFor(() => expect(state.page.value?.page).toBe(2));
    await vi.advanceTimersByTimeAsync(10_000);
    expect(mockedFetchOperationsQueuePage).toHaveBeenCalledTimes(1);

    pageNumber.value = 1;
    await vi.waitFor(() => expect(state.page.value?.page).toBe(1));
    const callsAfterNavigation = mockedFetchOperationsQueuePage.mock.calls.length;
    await vi.advanceTimersByTimeAsync(5_000);
    expect(mockedFetchOperationsQueuePage).toHaveBeenCalledTimes(callsAfterNavigation + 1);

    app.unmount();
  });
});
