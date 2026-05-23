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
      <DeckListCard
        v-for="deck in decks"
        :key="deck.id"
        :deck="deck"
        mode="browse"
        :title-to="`/decks/${deck.id}`"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useAuthStore } from '@/modules/auth/authStore';
import { fetchPublicDecks } from '@/modules/decks/api';
import DeckListCard from '@/modules/decks/components/DeckListCard.vue';
import type { DeckRecord } from '@/modules/decks/types';

const auth = useAuthStore();
const decks = ref<DeckRecord[]>([]);
const loading = ref(false);

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
