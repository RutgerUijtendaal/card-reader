<template>
  <div
    ref="referenceRef"
    class="relative w-full sm:w-80"
    @mouseenter="openHoverPanel"
    @mouseleave="scheduleCloseHoverPanel"
  >
    <img
      v-if="version.image_url"
      :src="toAbsoluteApiUrl(version.image_url)"
      alt="Card image"
      class="block w-full object-contain"
    >
    <p class="mt-2 text-center text-sm font-medium text-slate-700">
      Version {{ version.version_number }}
    </p>
    <p class="text-center text-xs text-slate-500">
      {{ formatDate(version.created_at) }}
    </p>

    <Teleport to="body">
      <aside
        v-if="showHoverPanel"
        ref="floatingRef"
        class="pointer-events-auto z-30 hidden w-96 rounded-xl border border-slate-200 bg-white p-4 opacity-100 shadow-2xl lg:block"
        :style="floatingPanelStyle"
        @mouseenter="cancelCloseHoverPanel"
        @mouseleave="scheduleCloseHoverPanel"
      >
        <CardHoverTooltip
          :item="version"
          :symbol-by-key="symbolByKey"
        />
      </aside>

      <aside
        v-if="showHoverPanel && isDev"
        class="pointer-events-auto z-30 hidden w-[28rem] rounded-xl border border-slate-300 bg-slate-950 p-4 text-slate-100 opacity-100 shadow-2xl lg:block"
        :style="debugPanelStyle"
        @mouseenter="cancelCloseHoverPanel"
        @mouseleave="scheduleCloseHoverPanel"
      >
        <h5 class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-300">
          Debug (Raw Version)
        </h5>
        <pre
          class="max-h-[22rem] overflow-auto whitespace-pre-wrap break-words text-[11px] leading-5"
        >{{ debugJson }}</pre>
      </aside>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, flip, offset, shift, useFloating } from '@floating-ui/vue';
import { computed, onBeforeUnmount, ref } from 'vue';
import { api, DEFAULT_API_BASE_URL } from '@/api/client';
import CardHoverTooltip from '@/components/cards/CardHoverTooltip.vue';
import type {
  CardHoverTooltipModel,
  CardTooltipSymbolLookup,
} from '@/components/cards/CardHoverTooltip.vue';

export type CardVersionGalleryItemModel = CardHoverTooltipModel & {
  image_url: string | null;
};

const props = defineProps<{
  version: CardVersionGalleryItemModel;
  symbolByKey: Record<string, CardTooltipSymbolLookup>;
}>();

const referenceRef = ref<HTMLElement | null>(null);
const floatingRef = ref<HTMLElement | null>(null);
const showHoverPanel = ref(false);
const isDev = import.meta.env.DEV;

let closeHoverPanelTimer: number | null = null;
const debugJson = computed(() => JSON.stringify(props.version, null, 2));

const { x, y, strategy } = useFloating(referenceRef, floatingRef, {
  open: showHoverPanel,
  placement: 'right-start',
  strategy: 'fixed',
  transform: false,
  middleware: [offset(12), flip(), shift({ padding: 8 })],
  whileElementsMounted: autoUpdate,
});

const floatingPanelStyle = computed(() => ({
  position: strategy.value,
  left: `${x.value ?? 0}px`,
  top: `${y.value ?? 0}px`,
}));

const debugPanelStyle = computed(() => ({
  position: strategy.value,
  left: `${(x.value ?? 0) + 420}px`,
  top: `${y.value ?? 0}px`,
}));

const openHoverPanel = (): void => {
  cancelCloseHoverPanel();
  showHoverPanel.value = true;
};

const cancelCloseHoverPanel = (): void => {
  if (closeHoverPanelTimer === null) return;
  window.clearTimeout(closeHoverPanelTimer);
  closeHoverPanelTimer = null;
};

const scheduleCloseHoverPanel = (): void => {
  cancelCloseHoverPanel();
  closeHoverPanelTimer = window.setTimeout(() => {
    closeHoverPanel();
  }, 30);
};

const closeHoverPanel = (): void => {
  cancelCloseHoverPanel();
  showHoverPanel.value = false;
};

onBeforeUnmount(() => {
  cancelCloseHoverPanel();
});

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};

const formatDate = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
};
</script>
