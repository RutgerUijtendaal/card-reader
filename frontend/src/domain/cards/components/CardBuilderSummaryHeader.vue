<template>
  <div class="relative">
    <div
      v-if="card?.image_url"
      class="absolute inset-0"
    >
      <img
        :src="toAbsoluteApiUrl(card.image_url)"
        :alt="card.name"
        class="h-full w-full object-cover"
        :style="{
          objectPosition: objectPosition,
          transform: imageTransform,
          opacity: imageOpacity,
        }"
      >
    </div>
    <div
      v-else
      class="absolute inset-0 theme-card-frame-muted"
    />
    <div
      v-if="card?.image_url"
      class="theme-art-scrim absolute inset-0"
    />

    <div class="relative flex min-h-[5.5rem] items-start gap-2 px-4 py-3">
      <button
        type="button"
        class="flex min-w-0 flex-1 items-start gap-3 text-left"
        @click="emit('activate')"
      >
        <div class="min-w-0 space-y-1">
          <p
            class="theme-display truncate text-xl"
            :class="card?.image_url ? 'theme-art-scrim-text' : 'theme-section-title'"
          >
            {{ name }}
          </p>
          <div
            class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs"
            :class="card?.image_url ? 'theme-art-scrim-text' : 'theme-section-muted'"
          >
            <span
              class="font-semibold uppercase tracking-[0.18em]"
              :class="card?.image_url ? 'theme-art-scrim-muted' : 'theme-kicker'"
            >{{
              boardLabel
            }}</span>
            <span class="font-semibold">{{ count }}</span>
            <span
              v-if="card"
              class="truncate"
            >
              {{ card.name }}
            </span>
            <span v-else>{{ emptyLabel }}</span>
          </div>
        </div>
      </button>

      <button
        type="button"
        class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition"
        :class="card?.image_url
          ? 'theme-art-scrim-text border-white/15 bg-white/10 hover:bg-white/20'
          : 'theme-section-title border-[var(--color-border-strong)] hover:bg-[var(--color-surface-soft)]'"
        :aria-label="actionLabel"
        @click="emit('activate')"
      >
        <ChevronDown
          class="h-4 w-4 transition-transform"
          :class="expanded ? 'rotate-180' : ''"
        />
      </button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next';
import type { CardListItem } from '@/domain/cards/types';
import { toAbsoluteApiUrl } from '@/shared/api/client';
withDefaults(
  defineProps<{
    name: string;
    card: CardListItem | null | undefined;
    boardLabel: string;
    count: number;
    emptyLabel: string;
    actionLabel: string;
    expanded: boolean;
    objectPosition?: string;
    imageTransform?: string;
    imageOpacity?: number;
  }>(),
  { objectPosition: 'center 30%', imageTransform: 'none', imageOpacity: 1 },
);
const emit = defineEmits<{ activate: [] }>();
</script>
