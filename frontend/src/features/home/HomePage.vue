<template>
  <AppPageLayout
    columns="one"
    root-class="min-h-full"
    main-class="app-page-single-column"
  >
    <div class="flex flex-col gap-14 py-4 sm:py-8 lg:gap-20 lg:py-12">
      <section class="grid items-center gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <div class="max-w-xl">
          <h1 class="home-headline theme-section-title">
            Explore every side of the game.
          </h1>
          <p class="theme-section-muted mt-5 text-base leading-7 sm:text-lg sm:leading-8">
            Browse the cards players bring to the table, discover the Evil forces waiting across
            from them, or turn a deck idea into your next game.
          </p>

          <div class="mt-8 flex flex-wrap gap-3">
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
            class="theme-link mt-5 inline-flex items-center gap-1.5 text-sm font-semibold"
            :data-testid="auth.authenticated ? 'home-decks-action' : 'home-playtester-action'"
          >
            {{ auth.authenticated ? 'Or browse public decks' : 'Or open Playtester' }}
          </RouterLink>
        </div>

        <figure class="min-w-0">
          <HomeCardFan :card-pool="workspace.activePool" />
          <figcaption class="theme-kicker mt-2 text-center text-sm">
            {{ showcaseCaption }}
          </figcaption>
        </figure>
      </section>

      <section aria-labelledby="home-collections-heading">
        <div class="mb-6">
          <h2
            id="home-collections-heading"
            class="theme-section-title theme-display text-2xl"
          >
            Choose a collection
          </h2>
          <p class="theme-section-muted mt-1 text-sm">
            Player and Evil are the two sides of the table. Neutral cards stand apart as their own
            smaller library.
          </p>
        </div>

        <div class="home-collections grid md:grid-cols-3">
          <RouterLink
            v-for="collection in collections"
            :key="collection.pool"
            :to="buildWorkspaceGallerySelectionLocation(collection.pool)"
            class="home-collection group"
            :class="{ 'home-collection-active': workspace.activePool === collection.pool }"
            :data-card-pool-link="collection.pool"
            :data-pool-tint="collection.pool"
          >
            <span class="flex items-center justify-between gap-3">
              <component
                :is="CARD_POOL_ICONS[collection.pool]"
                class="home-collection-icon h-6 w-6"
                :data-card-pool-icon="collection.pool"
                aria-hidden="true"
              />
              <span
                v-if="workspace.activePool === collection.pool"
                class="home-collection-current text-xs font-medium"
                data-current-workspace
              >
                Current workspace
              </span>
            </span>
            <span class="theme-section-title theme-display mt-5 block text-xl">
              {{ collection.title }}
            </span>
            <span class="theme-section-muted mt-2 block text-sm leading-6">
              {{ collection.description }}
            </span>
            <span class="home-collection-link mt-5 inline-flex text-sm font-semibold">
              {{ collection.linkLabel }}
            </span>
          </RouterLink>
        </div>
      </section>
    </div>
  </AppPageLayout>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { LogIn } from 'lucide-vue-next';
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
import HomeCardFan from '@/features/home/components/HomeCardFan.vue';

type HomeCollection = {
  pool: CardPool;
  title: string;
  description: string;
  linkLabel: string;
};

const collections: HomeCollection[] = [
  {
    pool: 'player',
    title: 'Build your side of the table',
    description:
      'Explore Heroes, mana, and the cards that become decks, opening hands, and playtests.',
    linkLabel: 'Browse Player cards',
  },
  {
    pool: 'evil',
    title: 'Discover what waits across from you',
    description:
      'Explore bosses, locations, and the Order, Blood, Dark, Metal, and Fire factions.',
    linkLabel: 'Browse Evil cards',
  },
  {
    pool: 'neutral',
    title: 'Stand apart from both sides',
    description: 'Browse the smaller library of cards outside the Player and Evil collections.',
    linkLabel: 'Browse Neutral cards',
  },
];

const SHOWCASE_CAPTIONS: Record<CardPool, string> = {
  player: 'Heroes from the Player collection',
  evil: 'Bosses from the Evil collection',
  neutral: 'From the Neutral collection',
};

const auth = useAuthStore();
const workspace = useCardPoolWorkspaceStore();
const showcaseCaption = computed(() => SHOWCASE_CAPTIONS[workspace.activePool]);
const newDeckLocation = buildNewDeckEditorLocation();
const buildDeckSignInLocation: RouteLocationRaw = {
  path: '/login',
  query: {
    redirect: '/my/decks/new?return_to=my_decks',
  },
};
</script>

<style scoped>
.home-headline {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: clamp(2.5rem, 1.6rem + 3vw, 4.25rem);
  line-height: 1.04;
  letter-spacing: -0.02em;
}

.home-collections {
  border-top: 1px solid var(--color-border);
}

.home-collection {
  --pool-tint: var(--accent);
  display: block;
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--color-border);
  transition: background-color 200ms ease;
}

.home-collection[data-pool-tint='player'] {
  --pool-tint: var(--pool-player);
}

.home-collection[data-pool-tint='evil'] {
  --pool-tint: var(--pool-evil);
}

.home-collection[data-pool-tint='neutral'] {
  --pool-tint: var(--pool-neutral);
}

.home-collection-icon,
.home-collection-current,
.home-collection-link {
  color: var(--pool-tint);
}

.home-collection:hover .home-collection-link {
  text-decoration: underline;
  text-underline-offset: 4px;
}

.home-collection-active {
  box-shadow: inset 0 2px 0 var(--pool-tint);
}

@media (min-width: 768px) {
  .home-collection {
    padding: 1.75rem 1.75rem 2rem;
    border-bottom: 0;
  }

  .home-collection:first-child {
    padding-left: 0;
  }

  .home-collection + .home-collection {
    border-left: 1px solid var(--color-border);
  }
}

@media (prefers-reduced-motion: reduce) {
  .home-collection {
    transition: none;
  }
}
</style>
