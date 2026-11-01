<template>
  <div
    class="home-card-fan"
    :data-card-pool="cardPool"
    :aria-busy="state === 'loading'"
  >
    <template v-if="state === 'loading'">
      <div
        v-for="(slot, index) in fanSlots"
        :key="`placeholder-${index}`"
        class="home-card-fan-slot"
        :style="slot"
        aria-hidden="true"
      >
        <div class="theme-card-loading-shim h-full w-full rounded-[4.5%]" />
      </div>
    </template>

    <template v-else-if="state === 'ready'">
      <RouterLink
        v-for="(card, index) in cards"
        :key="card.id"
        :to="`/cards/${card.id}`"
        class="home-card-fan-slot home-card-fan-card"
        :style="fanSlots[index]"
        :aria-label="card.name"
      >
        <img
          :src="toAbsoluteApiUrl(card.image_url ?? '')"
          :alt="card.name"
          class="h-full w-full rounded-[4.5%] object-cover"
          loading="eager"
          draggable="false"
        >
      </RouterLink>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { fetchCards } from '@/domain/cards/api';
import type { CardPool } from '@/domain/cards/cardPools';
import type { CardListItem } from '@/domain/cards/types';
import { toAbsoluteApiUrl } from '@/shared/api/client';

const props = defineProps<{ cardPool: CardPool }>();

type FanState = 'loading' | 'ready' | 'empty';

const FAN_SIZE = 5;
// The cards a side of the table is known by: its Heroes, its Bosses, or simply its cards.
const SHOWCASE_ROLE: Record<CardPool, string | undefined> = {
  player: 'hero',
  evil: 'boss',
  neutral: undefined,
};

const state = ref<FanState>('loading');
const cards = ref<CardListItem[]>([]);
let requestId = 0;

const fanSlots = computed(() => {
  const count = state.value === 'ready' ? cards.value.length : FAN_SIZE;
  const middle = (count - 1) / 2;
  return Array.from({ length: count }, (_, index) => {
    const offset = index - middle;
    return {
      '--fan-rotate': `${offset * 7}deg`,
      '--fan-shift': `${offset * 34}%`,
      '--fan-drop': `${Math.abs(offset) * Math.abs(offset) * 3}%`,
      zIndex: String(10 - Math.round(Math.abs(offset) * 2)),
    };
  });
});

const loadShowcase = async (cardPool: CardPool): Promise<void> => {
  const currentRequest = ++requestId;
  state.value = 'loading';
  try {
    const role = SHOWCASE_ROLE[cardPool];
    const page = await fetchCards<CardListItem>({
      card_pool: cardPool,
      page_size: FAN_SIZE,
      ...(role ? { card_roles: role } : {}),
    });
    if (currentRequest !== requestId) {
      return;
    }
    cards.value = page.results.filter((card) => Boolean(card.image_url)).slice(0, FAN_SIZE);
    state.value = cards.value.length > 0 ? 'ready' : 'empty';
  } catch {
    if (currentRequest === requestId) {
      cards.value = [];
      state.value = 'empty';
    }
  }
};

watch(
  () => props.cardPool,
  (cardPool) => {
    void loadShowcase(cardPool);
  },
  { immediate: true },
);
</script>

<style scoped>
.home-card-fan {
  position: relative;
  aspect-ratio: 16 / 11;
  width: 100%;
}

.home-card-fan-slot {
  position: absolute;
  left: 50%;
  top: 6%;
  width: 34%;
  aspect-ratio: 63 / 88;
  transform-origin: 50% 120%;
  transform: translateX(calc(-50% + var(--fan-shift))) translateY(var(--fan-drop)) rotate(var(--fan-rotate));
  /*
   * Card scans are several times larger than a fan slot. Drawn straight through a rotated
   * transform, Chromium resamples them with cheap filtering and the printed text aliases.
   * A compositing layer rasterizes the card upright with high-quality downscaling first,
   * then rotates that small bitmap.
   */
  will-change: transform;
}

.home-card-fan-card {
  display: block;
  border-radius: 4.5%;
  box-shadow:
    0 2px 4px rgba(4, 6, 18, 0.3),
    0 18px 40px -12px rgba(4, 6, 18, 0.55);
  transition:
    transform 260ms cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 260ms ease;
}

.home-card-fan-card:hover,
.home-card-fan-card:focus-visible {
  z-index: 20 !important;
  transform: translateX(calc(-50% + var(--fan-shift))) translateY(calc(var(--fan-drop) - 8%)) rotate(var(--fan-rotate)) scale(1.06);
  box-shadow:
    0 2px 4px rgba(4, 6, 18, 0.3),
    0 28px 60px -14px var(--accent-glow),
    0 24px 48px -16px rgba(4, 6, 18, 0.6);
}

@media (prefers-reduced-motion: reduce) {
  .home-card-fan-card {
    transition: none;
  }
}
</style>
