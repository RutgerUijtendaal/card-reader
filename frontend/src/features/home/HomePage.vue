<template>
  <AppPageLayout
    columns="one"
    root-class="min-h-full"
    main-class="app-page-single-column"
  >
    <div class="flex flex-col gap-10 py-3 sm:py-6 lg:py-10">
      <section
        class="home-hero relative overflow-hidden rounded-3xl border px-6 py-8 sm:px-9 sm:py-10"
      >
        <div class="relative z-10 max-w-3xl">
          <div class="mb-4 flex items-center gap-3">
            <span
              class="theme-selected-surface-strong flex h-11 w-11 items-center justify-center rounded-xl border"
            >
              <component
                :is="APP_SECTION_ICONS.home"
                class="h-5 w-5"
                aria-hidden="true"
              />
            </span>
            <p class="theme-kicker text-xs font-semibold uppercase tracking-[0.18em]">
              Maity's Card Game
            </p>
          </div>

          <h1
            class="theme-section-title max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl lg:text-5xl"
          >
            Explore every side of the game.
          </h1>
          <p class="theme-section-muted mt-4 max-w-2xl text-base leading-7 sm:text-lg">
            Browse the cards players bring to the table, discover the Evil forces waiting across
            from them, or turn a deck idea into your next game.
          </p>

          <div class="mt-7 flex flex-wrap gap-3">
            <RouterLink
              :to="auth.authenticated ? newDeckLocation : '/decks'"
              class="btn-primary gap-2"
              :data-testid="auth.authenticated ? 'home-build-deck-link' : 'home-decks-action'"
            >
              <component
                :is="auth.authenticated ? APP_SECTION_ICONS.deckBuilder : APP_SECTION_ICONS.decks"
                class="h-4 w-4"
                aria-hidden="true"
              />
              {{ auth.authenticated ? 'Build a deck' : 'Browse decks' }}
            </RouterLink>

            <RouterLink
              :to="auth.authenticated ? '/playtester' : buildDeckSignInLocation"
              class="btn-secondary gap-2"
              :data-testid="auth.authenticated ? 'home-playtester-action' : 'home-build-sign-in-link'"
            >
              <component
                :is="auth.authenticated ? APP_SECTION_ICONS.playtester : LogIn"
                class="h-4 w-4"
                aria-hidden="true"
              />
              {{ auth.authenticated ? 'Open Playtester' : 'Log in to build' }}
            </RouterLink>
          </div>

          <RouterLink
            :to="auth.authenticated ? '/decks' : '/playtester'"
            class="theme-link mt-4 inline-flex items-center gap-1.5 text-sm font-semibold"
            :data-testid="auth.authenticated ? 'home-decks-action' : 'home-playtester-action'"
          >
            {{ auth.authenticated ? 'Or browse public decks' : 'Or open Playtester' }}
            <ArrowRight
              class="h-4 w-4"
              aria-hidden="true"
            />
          </RouterLink>
        </div>

        <img
          :src="cardLogoUrl"
          alt=""
          class="pointer-events-none absolute -bottom-10 -right-8 h-52 w-52 rotate-6 object-contain opacity-[0.08] sm:h-64 sm:w-64"
        >
      </section>

      <section aria-labelledby="home-collections-heading">
        <div class="mb-4">
          <h2
            id="home-collections-heading"
            class="theme-section-title text-lg font-semibold"
          >
            Choose a collection
          </h2>
          <p class="theme-section-muted mt-1 text-sm">
            Player and Evil are the two main sides of the table. Neutral cards live alongside them
            as their own smaller library.
          </p>
        </div>

        <div class="grid gap-4 md:grid-cols-2">
          <RouterLink
            v-for="collection in primaryCollections"
            :key="collection.pool"
            :to="buildWorkspaceGallerySelectionLocation(collection.pool)"
            class="home-collection theme-card-frame group rounded-2xl p-5 transition sm:p-6"
            :class="{ 'home-collection-active': workspace.activePool === collection.pool }"
            :data-card-pool-link="collection.pool"
          >
            <div class="flex items-start justify-between gap-4">
              <span
                class="theme-selected-surface flex h-11 w-11 items-center justify-center rounded-xl border"
              >
                <component
                  :is="CARD_POOL_ICONS[collection.pool]"
                  class="h-5 w-5"
                  :data-card-pool-icon="collection.pool"
                  aria-hidden="true"
                />
              </span>
              <span
                v-if="workspace.activePool === collection.pool"
                class="theme-kicker rounded-full px-2.5 py-1 text-xs font-semibold"
                data-current-workspace
              >
                Current workspace
              </span>
            </div>
            <p class="theme-kicker mt-5 text-xs font-semibold uppercase tracking-[0.16em]">
              {{ collection.label }} collection
            </p>
            <h3 class="theme-section-title mt-2 text-xl font-semibold">
              {{ collection.title }}
            </h3>
            <p class="theme-section-muted mt-2 text-sm leading-6">
              {{ collection.description }}
            </p>
            <span class="theme-link mt-5 inline-flex items-center gap-1.5 text-sm font-semibold">
              {{ collection.linkLabel }}
              <component
                :is="ArrowRight"
                class="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                aria-hidden="true"
              />
            </span>
          </RouterLink>
        </div>

        <RouterLink
          :to="buildWorkspaceGallerySelectionLocation('neutral')"
          class="home-collection theme-card-frame-muted group mt-4 flex flex-col gap-4 rounded-2xl p-5 transition sm:flex-row sm:items-center"
          :class="{ 'home-collection-active': workspace.activePool === 'neutral' }"
          data-card-pool-link="neutral"
        >
          <span
            class="theme-card-frame theme-section-title flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
          >
            <component
              :is="CARD_POOL_ICONS.neutral"
              class="h-5 w-5"
              data-card-pool-icon="neutral"
              aria-hidden="true"
            />
          </span>
          <span class="min-w-0 flex-1">
            <span class="theme-section-title block font-semibold">Neutral collection</span>
            <span class="theme-section-muted mt-1 block text-sm">
              Browse cards that stand apart from the Player and Evil libraries.
            </span>
          </span>
          <span
            v-if="workspace.activePool === 'neutral'"
            class="theme-kicker rounded-full px-2.5 py-1 text-xs font-semibold"
            data-current-workspace
          >
            Current workspace
          </span>
          <span class="theme-link inline-flex items-center gap-1.5 text-sm font-semibold">
            Browse Neutral
            <ArrowRight
              class="h-4 w-4 transition-transform group-hover:translate-x-0.5"
              aria-hidden="true"
            />
          </span>
        </RouterLink>
      </section>
    </div>
  </AppPageLayout>
</template>

<script setup lang="ts">
import { ArrowRight, LogIn } from 'lucide-vue-next';
import type { RouteLocationRaw } from 'vue-router';
import { RouterLink } from 'vue-router';
import {
  buildWorkspaceGallerySelectionLocation,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';
import { CARD_POOL_ICONS } from '@/domain/cards/cardPoolIcons';
import type { CardPool } from '@/domain/cards/cardPools';
import { buildNewDeckEditorLocation } from '@/domain/decks/utils/deckRouteState';
import { useAuthStore } from '@/domain/session/store';
import AppPageLayout from '@/shared/components/app/AppPageLayout.vue';
import { APP_SECTION_ICONS } from '@/shared/components/app/appSectionIcons';

type HomeCollection = {
  pool: CardPool;
  label: string;
  title: string;
  description: string;
  linkLabel: string;
};

const primaryCollections: HomeCollection[] = [
  {
    pool: 'player',
    label: 'Player',
    title: 'Build your side of the table',
    description:
      'Explore Heroes, mana, and the cards that become decks, opening hands, and playtests.',
    linkLabel: 'Browse Player cards',
  },
  {
    pool: 'evil',
    label: 'Evil',
    title: 'Discover what waits across from you',
    description:
      'Explore bosses, locations, and the Order, Blood, Dark, Metal, and Fire factions.',
    linkLabel: 'Browse Evil cards',
  },
];

const auth = useAuthStore();
const workspace = useCardPoolWorkspaceStore();
const cardLogoUrl = `${import.meta.env.BASE_URL}card_logo_transparent.webp`;
const newDeckLocation = buildNewDeckEditorLocation();
const buildDeckSignInLocation: RouteLocationRaw = {
  path: '/login',
  query: {
    redirect: '/my/decks/new?return_to=my_decks',
  },
};
</script>

<style scoped>
.home-hero {
  border-color: color-mix(in srgb, var(--color-selected-border) 70%, var(--color-border));
  background:
    radial-gradient(
      circle at 88% 12%,
      color-mix(in srgb, var(--color-selected-bg-strong) 74%, transparent) 0%,
      transparent 42%
    ),
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--color-surface-strong) 92%, transparent) 0%,
      color-mix(in srgb, var(--color-selected-bg) 38%, var(--color-surface)) 100%
    );
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--color-surface-strong) 76%, transparent),
    0 18px 42px color-mix(in srgb, var(--color-border) 24%, transparent);
}

.home-collection-active {
  border-color: color-mix(in srgb, var(--color-selected-border) 76%, var(--color-border));
}

.home-collection:hover {
  border-color: var(--color-selected-border);
  transform: translateY(-2px);
}

@media (prefers-reduced-motion: reduce) {
  .home-collection {
    transition: none;
  }

  .home-collection:hover {
    transform: none;
  }
}
</style>
