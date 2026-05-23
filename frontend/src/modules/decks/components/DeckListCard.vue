<template>
  <div :class="layoutClass">
    <div :class="mediaRowClass">
      <div
        class="theme-card-frame-muted theme-card-image-well flex shrink-0 items-center justify-center rounded-xl"
        :class="imageFrameClass"
      >
        <img
          v-if="deck.hero_card.image_url"
          :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
          :alt="deck.hero_card.name"
          class="h-full w-full object-contain"
        >
        <div
          v-else
          class="theme-kicker text-xs"
        >
          No image
        </div>
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <component
            :is="titleTo ? 'RouterLink' : 'h3'"
            :to="titleTo"
            class="theme-section-title text-lg font-semibold"
            :class="titleTo ? 'truncate' : ''"
          >
            {{ deck.name }}
          </component>
          <span
            v-if="mode === 'owned'"
            class="theme-pill text-xs"
            :class="deck.is_public ? 'theme-pill-accent' : 'theme-pill-neutral'"
          >
            {{ deck.is_public ? 'Public' : 'Private' }}
          </span>
          <span
            v-else
            class="theme-pill theme-pill-accent text-xs"
          >
            {{ deck.mainboard.total_cards }} cards
          </span>
        </div>

        <div
          v-if="mode === 'owned'"
          class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm"
        >
          <span class="theme-section-muted">
            <span class="theme-section-title font-medium">Cards</span>
            {{ deck.mainboard.total_cards }} / 60
          </span>
          <span class="theme-section-muted">
            <span class="theme-section-title font-medium">Unique</span>
            {{ deck.mainboard.unique_cards }}
          </span>
          <span class="theme-section-muted">
            <span class="theme-section-title font-medium">Status</span>
            {{ deck.status.label }}
          </span>
        </div>

        <p class="theme-section-muted mt-1 text-sm">
          Hero: {{ deck.hero_card.name }}
        </p>
        <p
          v-if="mode === 'browse'"
          class="theme-section-muted text-sm"
        >
          By {{ deck.owner.username }}
        </p>
        <p
          v-else-if="deck.status.issues.length > 0"
          class="theme-section-muted mt-1 text-sm"
        >
          {{ deck.status.issues[0] }}
        </p>
        <p
          v-if="deck.description"
          class="theme-section-title mt-2 text-sm"
        >
          {{ deck.description }}
        </p>
        <p
          v-if="mode === 'browse'"
          class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]"
        >
          Updated {{ formatDate(deck.updated_at) }}
        </p>
      </div>
    </div>

    <div
      v-if="$slots.actions"
      class="flex flex-wrap gap-2"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import type { DeckRecord } from '@/modules/decks/types';

const props = defineProps<{
  deck: DeckRecord;
  mode: 'browse' | 'owned';
  titleTo?: string;
}>();

const formatDate = (value: string): string => new Date(value).toLocaleDateString();
const layoutClass = computed(() =>
  props.mode === 'browse'
    ? 'page-card flex gap-4 transition hover:-translate-y-0.5'
    : 'page-card flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between',
);
const mediaRowClass = computed(() => (props.mode === 'browse' ? 'flex min-w-0 flex-1 gap-4' : 'flex min-w-0 gap-4'));
const imageFrameClass = computed(() => (props.mode === 'browse' ? 'h-36 w-28' : 'h-32 w-24'));
</script>
