<template>
  <div aria-label="Card version change">
    <p class="theme-section-muted mb-3 text-[11px] font-semibold uppercase tracking-wide">
      Version change
    </p>
    <div
      v-if="!loadError"
      class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-center"
      :aria-label="loading ? 'Loading card version comparison' : undefined"
    >
      <template
        v-for="(item, index) in comparisonItems"
        :key="item.label"
      >
        <section class="min-w-0">
          <div class="mb-2 flex items-center justify-between gap-2">
            <p class="theme-section-title text-xs font-semibold uppercase tracking-wide">
              {{ item.label }}
            </p>
            <span
              v-if="!loading"
              class="theme-section-muted text-xs"
            >
              Printing {{ item.card?.version_number ?? 'unavailable' }}
            </span>
          </div>

          <div
            v-if="loading"
            class="mx-auto aspect-[63/88] max-w-full overflow-hidden rounded-xl"
            :style="comparisonCardStyle"
          >
            <CardLoadingSkeleton />
          </div>
          <CardGalleryItem
            v-else-if="item.card"
            :card="item.card"
            :card-height-rem="comparisonCardHeightRem"
            :hover-mode="effectiveHoverMode"
            activation-mode="emit"
            :activation-label="`Open ${item.label.toLowerCase()} version of ${item.card.name}`"
            @activate="emit('open-card', item.card.version_id)"
          />
          <div
            v-else
            class="theme-card-frame-muted theme-section-muted mx-auto flex aspect-[63/88] max-w-full items-center justify-center rounded-xl px-3 text-center text-xs"
            :style="comparisonCardStyle"
          >
            This printing is unavailable.
          </div>
        </section>

        <div
          v-if="index === 0"
          class="theme-card-frame-muted theme-section-title mx-auto flex h-9 w-9 shrink-0 rotate-90 items-center justify-center rounded-full sm:rotate-0"
          data-testid="version-change-arrow"
          aria-hidden="true"
        >
          <ArrowRight class="h-4 w-4" />
        </div>
      </template>
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
import { ArrowRight } from 'lucide-vue-next';
import { computed, onMounted, ref } from 'vue';
import { api } from '@/api/client';
import CardGalleryItem from '@/components/cards/CardGalleryItem.vue';
import CardLoadingSkeleton from '@/components/cards/CardLoadingSkeleton.vue';
import { useGalleryOptions } from '@/composables/useGalleryOptions';
import { useHoverModeSurface } from '@/composables/useHoverModePreferences';
import type { CardListItem, CardVersionDetail } from '@/modules/card-detail/types';
import type { NotificationCardVersionComparison } from '@/modules/notifications/utils/notificationPresentation';

const props = defineProps<{
  comparison: NotificationCardVersionComparison;
}>();

const emit = defineEmits<{
  'open-card': [versionId: string];
}>();

const { effectiveHoverMode } = useHoverModeSurface('notifications');
const { cardScale } = useGalleryOptions();
const versions = ref<CardVersionDetail[]>([]);
const loading = ref(true);
const loadError = ref(false);
const comparisonCardHeightRem = computed(() => Number((27 * cardScale.value).toFixed(2)));
const comparisonCardWidthRem = computed(() => Number(((comparisonCardHeightRem.value * 63) / 88).toFixed(2)));
const comparisonCardStyle = computed(() => ({ width: `${comparisonCardWidthRem.value}rem` }));

const toCardListItem = (version: CardVersionDetail): CardListItem => ({
  ...version,
  result_type: 'card',
});

const versionById = computed(() =>
  new Map(versions.value.map((version) => [version.version_id, toCardListItem(version)])),
);

const comparisonItems = computed(() => [
  {
    label: 'Before',
    card: versionById.value.get(props.comparison.beforeVersionId) ?? null,
  },
  {
    label: 'After',
    card: versionById.value.get(props.comparison.afterVersionId) ?? null,
  },
]);

onMounted(async () => {
  try {
    const response = await api.get<CardVersionDetail[]>(`/cards/${props.comparison.cardId}/generations`);
    versions.value = response.data;
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
});
</script>
