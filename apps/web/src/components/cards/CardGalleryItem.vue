<template>
  <div
    ref="referenceRef"
    class="relative w-full sm:w-80"
    @mouseenter="openHoverPanel"
    @mouseleave="scheduleCloseHoverPanel"
  >
    <component
      :is="canOpenCardDetail ? 'RouterLink' : 'div'"
      v-bind="canOpenCardDetail ? { to: `/cards/${card.id}` } : {}"
      :class="[
        'block',
        canOpenCardDetail ? 'transition hover:drop-shadow-lg' : 'cursor-default',
      ]"
    >
      <img
        v-if="card.image_url"
        :src="toAbsoluteApiUrl(card.image_url)"
        alt="Card image"
        class="block w-full object-contain"
        loading="lazy"
        decoding="async"
      >
    </component>

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
          :item="card"
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
          Debug (Raw Card)
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
import { useAuthStore } from '@/modules/auth/authStore';
import type {
  CardHoverTooltipModel,
  CardTooltipSymbolLookup,
} from '@/components/cards/CardHoverTooltip.vue';

export type CardGalleryItemModel = CardHoverTooltipModel & {
  image_url: string | null;
};

const props = defineProps<{
  card: CardGalleryItemModel;
  symbolByKey: Record<string, CardTooltipSymbolLookup>;
}>();

const referenceRef = ref<HTMLElement | null>(null);
const floatingRef = ref<HTMLElement | null>(null);
const showHoverPanel = ref(false);
const isDev = import.meta.env.DEV;
const auth = useAuthStore();

let closeHoverPanelTimer: number | null = null;
const debugJson = computed(() => JSON.stringify(props.card, null, 2));
const canOpenCardDetail = computed(() => auth.canAccessStaffRoutes);

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
</script>
