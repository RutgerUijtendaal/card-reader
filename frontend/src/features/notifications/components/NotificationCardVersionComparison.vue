<template>
  <div aria-label="Card version change">
    <div class="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <p class="theme-section-muted text-[11px] font-semibold uppercase tracking-wide">
        Visual comparison
      </p>
      <p
        v-if="!loading && !loadError"
        class="theme-section-muted text-xs"
      >
        Drag across the card to reveal each printing
      </p>
    </div>

    <div
      v-if="loading"
      class="mx-auto aspect-[63/88] max-w-full overflow-hidden rounded-2xl"
      :style="comparisonCardStyle"
      aria-label="Loading card version comparison"
    >
      <CardLoadingSkeleton />
    </div>

    <div
      v-else-if="beforeCard && afterCard && beforeCard.image_url && afterCard.image_url"
      class="mx-auto max-w-full"
      :style="comparisonCardStyle"
    >
      <div class="mb-2 flex items-center justify-between gap-3">
        <button
          class="comparison-version-link theme-section-title min-w-0 text-left"
          data-testid="comparison-before-link"
          type="button"
          :aria-label="`Open before version, printing ${beforeCard.version_number}`"
          @click="emit('open-card', beforeCard.version_id)"
        >
          <span class="block text-[11px] font-semibold uppercase tracking-wide">Before</span>
          <span class="theme-section-muted mt-0.5 block text-xs">
            Printing {{ beforeCard.version_number }}
          </span>
        </button>

        <button
          class="comparison-version-link theme-section-title min-w-0 text-right"
          data-testid="comparison-after-link"
          type="button"
          :aria-label="`Open after version, printing ${afterCard.version_number}`"
          @click="emit('open-card', afterCard.version_id)"
        >
          <span class="block text-[11px] font-semibold uppercase tracking-wide">After</span>
          <span class="theme-section-muted mt-0.5 block text-xs">
            Printing {{ afterCard.version_number }}
          </span>
        </button>
      </div>

      <div
        class="comparison-viewer theme-card-image-well relative aspect-[63/88] overflow-hidden rounded-2xl"
        :style="comparisonViewerStyle"
        data-testid="version-comparison-viewer"
      >
        <img
          :src="toAbsoluteApiUrl(afterCard.image_url)"
          :alt="`${afterCard.name}, after version`"
          class="absolute inset-0 h-full w-full object-contain"
          draggable="false"
        >
        <div
          class="comparison-before-layer pointer-events-none absolute inset-0 overflow-hidden"
          aria-hidden="true"
        >
          <img
            :src="toAbsoluteApiUrl(beforeCard.image_url)"
            alt=""
            class="absolute inset-0 h-full w-full max-w-none object-contain"
            draggable="false"
          >
        </div>

        <div
          class="comparison-divider pointer-events-none absolute inset-y-0"
          aria-hidden="true"
        >
          <span class="comparison-handle">
            <ChevronsLeftRight class="h-4 w-4" />
          </span>
        </div>

        <input
          v-model.number="comparisonPosition"
          class="comparison-range absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
          type="range"
          min="0"
          max="100"
          step="1"
          aria-label="Reveal before and after card versions"
          :aria-valuetext="`${comparisonPosition}% before, ${100 - comparisonPosition}% after`"
          data-testid="version-comparison-slider"
        >
      </div>

      <div
        class="comparison-presets theme-card-frame-muted mt-2 grid grid-cols-[1fr_auto_1fr] overflow-hidden rounded-lg"
        aria-label="Comparison display shortcuts"
      >
        <button
          class="comparison-preset justify-start"
          :class="comparisonPosition === 0 ? 'comparison-preset-active' : ''"
          type="button"
          :aria-pressed="comparisonPosition === 0"
          aria-label="Show only the after version"
          @click="comparisonPosition = 0"
        >
          <ArrowLeft class="h-3.5 w-3.5" />
          After
        </button>
        <button
          class="comparison-preset border-x"
          :class="comparisonPosition === 50 ? 'comparison-preset-active' : ''"
          type="button"
          :aria-pressed="comparisonPosition === 50"
          aria-label="Show a split comparison"
          @click="comparisonPosition = 50"
        >
          Split
        </button>
        <button
          class="comparison-preset justify-end"
          :class="comparisonPosition === 100 ? 'comparison-preset-active' : ''"
          type="button"
          :aria-pressed="comparisonPosition === 100"
          aria-label="Show only the before version"
          @click="comparisonPosition = 100"
        >
          Before
          <ArrowRight class="h-3.5 w-3.5" />
        </button>
      </div>

      <p class="theme-section-muted mt-1.5 text-center text-[11px]">
        Drag the divider or use the arrow keys for precise comparison
      </p>
    </div>

    <p
      v-else
      class="theme-section-muted text-sm"
      role="status"
    >
      The card version comparison is unavailable.
    </p>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, ArrowRight, ChevronsLeftRight } from 'lucide-vue-next';
import { computed, onMounted, ref } from 'vue';
import { fetchCardVersions } from '@/domain/cards/api';
import CardLoadingSkeleton from '@/domain/cards/components/CardLoadingSkeleton.vue';
import { useGalleryOptions } from '@/domain/cards/composables/useGalleryOptions';
import type { CardListItem, CardVersionDetail } from '@/domain/cards/types';
import type { NotificationCardVersionComparison } from '@/features/notifications/utils/notificationPresentation';
import { toAbsoluteApiUrl } from '@/shared/api/client';

const props = defineProps<{
  comparison: NotificationCardVersionComparison;
}>();

const emit = defineEmits<{
  'open-card': [versionId: string];
}>();

const { cardScale } = useGalleryOptions();
const versions = ref<CardVersionDetail[]>([]);
const loading = ref(true);
const loadError = ref(false);
const comparisonPosition = ref(50);
const comparisonCardHeightRem = computed(() => Number((27 * cardScale.value).toFixed(2)));
const comparisonCardWidthRem = computed(() => Number(((comparisonCardHeightRem.value * 63) / 88).toFixed(3)));
const comparisonCardStyle = computed(() => ({
  width: `${comparisonCardWidthRem.value}rem`,
}));
const comparisonViewerStyle = computed<Record<string, string>>(() => ({
  '--comparison-position': `${comparisonPosition.value}%`,
}));

const toCardListItem = (version: CardVersionDetail): CardListItem => ({
  ...version,
  result_type: 'card',
});

const versionById = computed(() =>
  new Map(versions.value.map((version) => [version.version_id, toCardListItem(version)])),
);
const beforeCard = computed(() => versionById.value.get(props.comparison.beforeVersionId) ?? null);
const afterCard = computed(() => versionById.value.get(props.comparison.afterVersionId) ?? null);

onMounted(async () => {
  try {
    versions.value = await fetchCardVersions(props.comparison.cardId);
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.comparison-version-link {
  border-radius: 0.5rem;
  transition:
    color 150ms ease,
    opacity 150ms ease;
}

.comparison-version-link:hover {
  color: var(--theme-accent);
}

.comparison-version-link:focus-visible {
  outline: 2px solid var(--theme-accent);
  outline-offset: 3px;
}

.comparison-preset {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.25rem;
  border-color: var(--color-border);
  padding: 0.4rem 0.6rem;
  color: var(--color-text-muted);
  font-size: 0.6875rem;
  font-weight: 650;
  transition:
    background-color 150ms ease,
    color 150ms ease;
}

.comparison-preset:hover,
.comparison-preset-active {
  background: var(--color-surface-strong);
  color: var(--color-text);
}

.comparison-preset:focus-visible {
  position: relative;
  z-index: 1;
  outline: 2px solid var(--theme-accent);
  outline-offset: -2px;
}

.comparison-viewer {
  isolation: isolate;
  box-shadow:
    0 16px 32px color-mix(in srgb, var(--color-text) 14%, transparent),
    0 0 0 1px var(--color-border);
}

.comparison-before-layer {
  clip-path: inset(0 calc(100% - var(--comparison-position)) 0 0);
}

.comparison-divider {
  left: var(--comparison-position);
  z-index: 3;
  width: 2px;
  transform: translateX(-1px);
  background: rgb(255 255 255 / 92%);
  box-shadow: 0 0 0 1px rgb(15 23 42 / 24%);
}

.comparison-handle {
  position: absolute;
  left: 50%;
  top: 50%;
  display: flex;
  height: 2.25rem;
  width: 2.25rem;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(255 255 255 / 60%);
  border-radius: 999px;
  background: rgb(15 23 42 / 82%);
  color: white;
  box-shadow: 0 4px 12px rgb(15 23 42 / 34%);
  transform: translate(-50%, -50%);
  backdrop-filter: blur(6px);
}

.comparison-viewer:focus-within {
  box-shadow:
    0 16px 32px color-mix(in srgb, var(--color-text) 14%, transparent),
    0 0 0 3px color-mix(in srgb, var(--theme-accent) 68%, transparent);
}
</style>
