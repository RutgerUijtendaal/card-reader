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
      class="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-slate-900/74 to-slate-900/28"
    />

    <div class="relative flex min-h-[5.5rem] items-start gap-2 px-4 py-3">
      <button
        type="button"
        class="flex min-w-0 flex-1 items-start gap-3 text-left"
        @click="emit('activate')"
      >
        <div class="min-w-0 space-y-1">
          <p class="truncate text-lg font-semibold text-white">
            {{ name }}
          </p>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-100/90">
            <span class="font-semibold uppercase tracking-[0.18em] text-slate-200/70">{{
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
        class="theme-card-frame-muted theme-section-title inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition"
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
