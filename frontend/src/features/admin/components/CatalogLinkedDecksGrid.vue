<template>
  <div
    v-if="decks.length > 0"
    class="grid gap-2 sm:grid-cols-2"
  >
    <component
      :is="deck.visibility === 'private' ? 'div' : RouterLink"
      v-for="deck in decks"
      :key="deck.id"
      :to="deck.visibility === 'private' ? undefined : `/decks/${deck.id}`"
      class="theme-card-frame flex min-w-0 items-center gap-3 rounded-lg p-2"
    >
      <div class="theme-card-image-well h-16 w-12 shrink-0 overflow-hidden rounded-md">
        <img
          v-if="deck.hero_card.image_url"
          :src="toAbsoluteApiUrl(deck.hero_card.image_url)"
          :alt="deck.hero_card.name"
          class="h-full w-full object-cover"
        >
      </div>
      <div class="min-w-0 flex-1">
        <p class="theme-section-title truncate text-sm font-semibold">
          {{ deck.name }}
        </p>
        <p class="theme-section-muted truncate text-xs">
          {{ deck.owner.username }}
        </p>
        <span class="theme-pill theme-pill-neutral mt-1 inline-flex text-[11px]">{{
          deck.visibility
        }}</span>
      </div>
    </component>
  </div>
  <div
    v-else
    class="theme-empty-state px-3 py-6 text-center"
  >
    {{ emptyMessage }}
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import type { LinkedDeckPreview } from '@/features/admin/types';

defineProps<{ decks: LinkedDeckPreview[]; emptyMessage: string }>();
</script>
