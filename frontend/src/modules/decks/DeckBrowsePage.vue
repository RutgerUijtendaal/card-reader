<template>
  <section class="space-y-5">
    <div class="page-card flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="theme-section-title text-xl font-semibold">
          Decks
        </h2>
        <p class="theme-section-muted text-sm">
          Browse public decks and inspect their hero plus full mainboard.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <RouterLink
          v-if="auth.authenticated"
          class="btn-secondary"
          to="/my/decks"
        >
          My Decks
        </RouterLink>
        <RouterLink
          v-if="auth.authenticated"
          class="btn-primary"
          to="/my/decks/new"
        >
          New Deck
        </RouterLink>
      </div>
    </div>

    <div
      v-if="loading"
      class="page-card theme-section-muted text-sm"
    >
      Loading decks...
    </div>

    <div
      v-else-if="decks.length === 0"
      class="page-card theme-section-muted text-sm"
    >
      No public decks yet.
    </div>

    <div
      v-else
      class="grid gap-4 lg:grid-cols-2"
    >
      <RouterLink
        v-for="deck in decks"
        :key="deck.id"
        :to="`/decks/${deck.id}`"
        class="page-card flex gap-4 transition hover:-translate-y-0.5"
      >
        <div class="theme-card-frame-muted theme-card-image-well flex h-36 w-28 shrink-0 items-center justify-center rounded-xl">
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

        <div class="min-w-0 flex-1 space-y-2">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="theme-section-title truncate text-lg font-semibold">
              {{ deck.name }}
            </h3>
            <span class="theme-pill theme-pill-accent text-xs">
              {{ deck.mainboard.total_cards }} cards
            </span>
          </div>
          <p class="theme-section-muted text-sm">
            Hero: {{ deck.hero_card.name }}
          </p>
          <p class="theme-section-muted text-sm">
            By {{ deck.owner.username }}
          </p>
          <p
            v-if="deck.description"
            class="theme-section-title text-sm"
          >
            {{ deck.description }}
          </p>
          <p class="theme-kicker text-xs font-medium uppercase tracking-[0.16em]">
            Updated {{ formatDate(deck.updated_at) }}
          </p>
        </div>
      </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { toAbsoluteApiUrl } from '@/api/client';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchPublicDecks } from '@/modules/decks/api';
import type { DeckRecord } from '@/modules/decks/types';

const auth = useAuthStore();
const decks = ref<DeckRecord[]>([]);
const loading = ref(false);

const formatDate = (value: string): string => new Date(value).toLocaleDateString();

const loadDecks = async (): Promise<void> => {
  loading.value = true;
  try {
    decks.value = await fetchPublicDecks();
  } finally {
    loading.value = false;
  }
};

onMounted(loadDecks);
</script>
