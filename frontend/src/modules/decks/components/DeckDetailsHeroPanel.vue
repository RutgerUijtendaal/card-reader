<template>
  <AppStickyAside
    side="left"
  >
    <div class="space-y-5">
      <div class="space-y-1">
        <h3 class="theme-section-title text-lg font-semibold">
          Hero
        </h3>
        <p class="theme-section-muted text-sm">
          The hero determines which cards belong in this deck.
        </p>
      </div>

      <div
        v-if="controller.deck.selectedHero.value"
        class="space-y-3"
      >
        <div
          v-if="controller.deck.selectedHero.value.image_url"
          class="mx-auto aspect-[63/88] w-full max-w-48 overflow-hidden rounded-xl"
        >
          <img
            :src="toAbsoluteApiUrl(controller.deck.selectedHero.value.image_url)"
            :alt="controller.deck.selectedHero.value.name"
            class="h-full w-full object-contain"
          >
        </div>
        <div
          v-else
          class="theme-empty-state mx-auto flex aspect-[63/88] w-full max-w-48 items-center justify-center rounded-xl text-sm"
        >
          No hero image
        </div>
        <p class="theme-section-title text-center font-semibold">
          {{ controller.deck.selectedHero.value.name }}
        </p>
      </div>

      <button
        class="btn-secondary w-full justify-center"
        type="button"
        @click="controller.beginHeroChange()"
      >
        Change hero
      </button>
    </div>
  </AppStickyAside>
</template>

<script setup lang="ts">
import { toAbsoluteApiUrl } from '@/api/client';
import AppStickyAside from '@/components/app/AppStickyAside.vue';
import type { DeckEditorController } from '@/modules/decks/composables/useDeckEditor';

defineProps<{
  controller: DeckEditorController;
}>();
</script>
