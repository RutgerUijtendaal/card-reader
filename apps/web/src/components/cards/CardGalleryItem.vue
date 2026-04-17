<template>
  <div
    ref="referenceRef"
    class="relative w-full sm:w-72"
    @mouseenter="openHoverPanel"
    @mouseleave="closeHoverPanel"
  >
    <RouterLink
      :to="`/cards/${card.id}`"
      class="block transition hover:drop-shadow-lg"
    >
      <img
        v-if="card.image_url"
        :src="toAbsoluteApiUrl(card.image_url)"
        alt="Card image"
        class="block w-full object-contain"
      />
    </RouterLink>

    <Teleport to="body">
      <aside
        v-if="showHoverPanel"
        ref="floatingRef"
        class="pointer-events-none z-30 hidden w-80 rounded-xl border border-slate-200 bg-white p-4 opacity-100 shadow-2xl lg:block"
        :style="{ position: 'fixed', left: `${panelX}px`, top: `${panelY}px` }"
      >
        <h4 class="text-base font-semibold text-slate-900">{{ card.name }}</h4>
        <p class="mb-3 text-xs text-slate-500">{{ card.type_line || 'No type' }}</p>

        <div class="grid grid-cols-2 gap-2 text-xs text-slate-700">
          <span>Mana: {{ card.mana_cost || '-' }}</span>
          <span>Conf: {{ card.confidence.toFixed(2) }}</span>
          <span>ATK: {{ card.attack ?? '-' }}</span>
          <span>HP: {{ card.health ?? '-' }}</span>
        </div>

        <div class="mt-3 flex flex-wrap gap-1 text-[11px]">
          <span
            v-for="keyword in card.keywords"
            :key="`kw-${card.id}-${keyword}`"
            class="rounded bg-sky-100 px-2 py-0.5 text-sky-800"
          >
            {{ keyword }}
          </span>
          <span
            v-for="tag in card.tags"
            :key="`tag-${card.id}-${tag}`"
            class="rounded bg-emerald-100 px-2 py-0.5 text-emerald-800"
          >
            {{ tag }}
          </span>
          <span
            v-for="type in card.types"
            :key="`type-${card.id}-${type}`"
            class="rounded bg-amber-100 px-2 py-0.5 text-amber-800"
          >
            {{ type }}
          </span>
        </div>

        <p class="mt-3 text-xs text-slate-400">Open card to view version history</p>
      </aside>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { autoUpdate, computePosition, flip, offset, shift } from '@floating-ui/dom';
import { nextTick, onBeforeUnmount, ref } from 'vue';
import { api } from '@/api/client';

export type CardGalleryItemModel = {
  id: string;
  name: string;
  type_line: string;
  mana_cost: string;
  attack: number | null;
  health: number | null;
  confidence: number;
  image_url: string | null;
  keywords: string[];
  tags: string[];
  symbols: string[];
  types: string[];
};

defineProps<{
  card: CardGalleryItemModel;
}>();

const referenceRef = ref<HTMLElement | null>(null);
const floatingRef = ref<HTMLElement | null>(null);
const showHoverPanel = ref(false);
const panelX = ref(0);
const panelY = ref(0);

let stopAutoUpdate: (() => void) | null = null;

const updatePosition = async (): Promise<void> => {
  const reference = referenceRef.value;
  const floating = floatingRef.value;
  if (!reference || !floating) return;

  const position = await computePosition(reference, floating, {
    placement: 'right-start',
    middleware: [offset(12), flip(), shift({ padding: 8 })]
  });
  panelX.value = position.x;
  panelY.value = position.y;
};

const openHoverPanel = async (): Promise<void> => {
  showHoverPanel.value = true;
  await nextTick();
  if (!showHoverPanel.value) return;
  await updatePosition();
  if (!showHoverPanel.value) return;

  const reference = referenceRef.value;
  const floating = floatingRef.value;
  if (!reference || !floating) return;

  stopAutoUpdate = autoUpdate(reference, floating, () => {
    void updatePosition();
  });
};

const closeHoverPanel = (): void => {
  showHoverPanel.value = false;
  if (stopAutoUpdate) {
    stopAutoUpdate();
    stopAutoUpdate = null;
  }
};

onBeforeUnmount(() => {
  if (stopAutoUpdate) {
    stopAutoUpdate();
    stopAutoUpdate = null;
  }
});

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? 'http://127.0.0.1:8000';
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};
</script>
