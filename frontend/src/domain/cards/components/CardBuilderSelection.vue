<template>
  <section class="space-y-3">
    <p class="theme-section-title text-sm font-semibold">
      {{ label }}
    </p>
    <div
      v-if="card"
      class="space-y-3"
    >
      <div
        v-if="card.image_url"
        class="mx-auto aspect-[63/88] max-h-[34rem] w-full rounded-xl"
      >
        <img
          :src="toAbsoluteApiUrl(card.image_url)"
          :alt="card.name"
          class="h-full w-full object-contain"
        >
      </div>
      <div
        v-else
        class="theme-empty-state flex h-[34rem] items-center justify-center rounded-xl text-sm"
      >
        No image
      </div>
      <p class="theme-section-title text-center text-sm font-semibold">
        {{ card.name }}
      </p>
    </div>
    <div
      v-else
      class="theme-card-frame mx-auto aspect-[63/88] max-h-[34rem] w-full overflow-hidden rounded-xl"
    >
      <CardLoadingSkeleton :animated="false" />
    </div>
    <slot />
  </section>
</template>
<script setup lang="ts">
import type { CardListItem } from '@/domain/cards/types';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import CardLoadingSkeleton from '@/domain/cards/components/CardLoadingSkeleton.vue';
defineProps<{ card: CardListItem | null | undefined; label: string }>();
</script>
