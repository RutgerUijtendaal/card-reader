<template>
  <section
    v-if="deck"
    class="space-y-5"
  >
    <div class="page-card flex flex-col gap-4 lg:flex-row lg:justify-between">
      <div class="min-w-0">
        <h2 class="theme-section-title text-xl font-semibold">
          {{ deck.name }}
        </h2>
        <p class="theme-section-muted text-sm">
          By {{ deck.owner.username }}
        </p>
        <p
          v-if="deck.description"
          class="theme-section-title mt-3 text-sm"
        >
          {{ deck.description }}
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <RouterLink
          class="btn-secondary"
          to="/decks"
        >
          Back to Decks
        </RouterLink>
        <RouterLink
          v-if="canEdit"
          class="btn-primary"
          :to="`/my/decks/${deck.id}/edit`"
        >
          Edit Deck
        </RouterLink>
      </div>
    </div>

    <div class="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div class="page-card space-y-4">
        <h3 class="theme-section-title text-base font-semibold">
          Hero
        </h3>
        <div class="theme-card-frame flex gap-4 rounded-xl p-4">
          <div class="theme-card-frame-muted theme-card-image-well flex h-44 w-32 shrink-0 items-center justify-center rounded-xl">
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
          <div class="min-w-0">
            <p class="theme-section-title text-lg font-semibold">
              {{ deck.hero_card.name }}
            </p>
            <p class="theme-section-muted text-sm">
              {{ deck.hero_card.label }}
            </p>
          </div>
        </div>
      </div>

      <div class="page-card space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h3 class="theme-section-title text-base font-semibold">
            Mainboard
          </h3>
          <span class="theme-pill theme-pill-accent text-xs">
            {{ deck.mainboard.total_cards }} cards / {{ deck.mainboard.unique_cards }} unique
          </span>
        </div>

        <div class="grid gap-3 md:grid-cols-2">
          <div
            v-for="entry in deck.mainboard.entries"
            :key="entry.card.id"
            class="theme-card-frame flex items-center gap-3 rounded-xl p-3"
          >
            <div class="theme-card-frame-muted theme-card-image-well flex h-24 w-16 shrink-0 items-center justify-center rounded-lg">
              <img
                v-if="entry.card.image_url"
                :src="toAbsoluteApiUrl(entry.card.image_url)"
                :alt="entry.card.name"
                class="h-full w-full object-contain"
              >
              <div
                v-else
                class="theme-kicker text-[11px]"
              >
                No image
              </div>
            </div>

            <div class="min-w-0 flex-1">
              <p class="theme-section-title truncate text-sm font-semibold">
                {{ entry.card.name }}
              </p>
              <p class="theme-section-muted text-xs">
                {{ entry.card.label }}
              </p>
            </div>

            <span class="theme-pill text-xs">
              x{{ entry.quantity }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <div
    v-else
    class="page-card theme-section-muted text-sm"
  >
    Loading deck...
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { toAbsoluteApiUrl } from '@/api/client';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchDeckDetail } from '@/modules/decks/api';
import type { DeckRecord } from '@/modules/decks/types';

const route = useRoute();
const auth = useAuthStore();
const deck = ref<DeckRecord | null>(null);

const canEdit = computed(() => deck.value?.owner.id === auth.user?.id);

const loadDeck = async (): Promise<void> => {
  deck.value = await fetchDeckDetail(String(route.params.id));
};

onMounted(loadDeck);
</script>
