import { computed, effectScope, ref, watch, type Ref } from 'vue';
import { useIntervalFn } from '@vueuse/core';
import { useRoute } from 'vue-router';

type PollingSummaryOptions = {
  canLoad: () => boolean;
  load: () => Promise<void>;
  reset: () => void;
  intervalMs?: number;
};

type PollingSummaryController = {
  loading: Ref<boolean>;
  load: () => Promise<void>;
};

const controllers = new Map<string, PollingSummaryController>();

export function usePollingSummary(key: string, options: PollingSummaryOptions): PollingSummaryController {
  const existing = controllers.get(key);
  if (existing) {
    return existing;
  }

  const loading = ref(false);
  const route = useRoute();
  const canLoad = computed(options.canLoad);
  const intervalMs = options.intervalMs ?? 60000;
  const scope = effectScope(true);

  const load = async (): Promise<void> => {
    if (!canLoad.value) {
      options.reset();
      return;
    }
    loading.value = true;
    try {
      await options.load();
    } catch {
      options.reset();
    } finally {
      loading.value = false;
    }
  };

  scope.run(() => {
    useIntervalFn(
      () => {
        void load();
      },
      intervalMs,
      { immediate: false },
    );

    watch(canLoad, () => {
      void load();
    });

    watch(
      () => route.fullPath,
      () => {
        void load();
      },
    );
  });

  const controller = { loading, load };
  controllers.set(key, controller);
  void load();
  return controller;
}
