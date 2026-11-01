<template>
  <div class="grid items-start gap-8 2xl:grid-cols-[minmax(18rem,30rem)_minmax(24rem,1fr)]">
    <div class="px-2 py-2 sm:px-4">
      <img
        v-if="version.image_url"
        :src="toAbsoluteApiUrl(version.image_url)"
        alt="Selected card printing image"
        class="card-version-art mx-auto block h-auto max-h-[44rem] w-auto max-w-full"
      >
      <div
        v-else
        class="theme-empty-state flex h-80 items-center justify-center"
      >
        No image
      </div>
    </div>

    <section class="space-y-6">
      <div>
        <div class="flex min-w-0 items-start justify-between gap-3">
          <h3 class="theme-section-title theme-display min-w-0 text-3xl">
            {{ version.name || 'Unnamed Card' }}
          </h3>
          <div class="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <RouterLink
              v-for="group in cardGroups"
              :key="group.id"
              :to="buildCardGroupDetailLocation(group.id, route.query, group.card_pool)"
              class="btn-secondary inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium"
            >
              <span>{{ group.name }}</span>
              <span class="theme-kicker">{{ group.member_count }} cards</span>
            </RouterLink>
            <button
              v-if="canFlag"
              class="btn-secondary inline-flex h-9 w-9 shrink-0 items-center justify-center p-0"
              type="button"
              title="Flag a parsed property that looks incorrect so staff can review and correct it."
              aria-label="Flag parse issue"
              @click="$emit('flag-parse-issue')"
            >
              <Flag class="h-4 w-4" />
            </button>
          </div>
        </div>
        <p class="theme-kicker mt-1 text-xs font-semibold uppercase tracking-[0.16em]">
          Printing {{ version.version_number }}<span v-if="version.is_latest"> · Latest</span> · Version {{ formatCardContentVersion(version) }}
        </p>
      </div>

      <dl class="card-version-stats theme-divider grid grid-cols-3 border-y">
        <div class="card-version-stat">
          <dt class="card-version-label">
            <Sparkles class="card-version-icon" />
            <span>Mana</span>
          </dt>
          <dd class="mt-1">
            <SymbolizedText
              :tokens="version.mana_symbols"
              :text="version.mana_cost || '-'"
              :symbol-by-key="symbolByKey"
              class="theme-section-title text-sm"
            />
          </dd>
        </div>
        <div class="card-version-stat">
          <dt class="card-version-label">
            <Swords class="card-version-icon" />
            <span>Attack</span>
          </dt>
          <dd class="theme-section-title theme-display mt-1 text-xl">
            {{ version.attack ?? '-' }}
          </dd>
        </div>
        <div class="card-version-stat">
          <dt class="card-version-label">
            <HeartPulse class="card-version-icon" />
            <span>Health</span>
          </dt>
          <dd class="theme-section-title theme-display mt-1 text-xl">
            {{ version.health ?? '-' }}
          </dd>
        </div>
      </dl>

      <div>
        <div class="card-version-label mb-3">
          <BookOpenText class="card-version-icon" />
          <span>Rules Text</span>
        </div>
        <div class="card-version-rules text-sm">
          <CardMarkupText
            v-if="version.rules_text_enriched"
            class="theme-section-title"
            :markup="version.rules_text_enriched"
            :symbols="version.symbols"
          />
          <p
            v-else
            class="theme-section-muted"
          >
            -
          </p>
        </div>
      </div>

      <dl class="theme-divider divide-y divide-[var(--color-border)] border-y">
        <div class="card-version-row">
          <dt class="card-version-label">
            <ScrollText class="card-version-icon" />
            <span>Type</span>
          </dt>
          <dd class="flex flex-wrap gap-1.5">
            <span
              v-for="type in version.types"
              :key="type.id"
              class="theme-pill theme-pill-warning px-2 py-0.5 text-xs font-semibold"
            >
              {{ type.label }}
            </span>
            <span
              v-if="version.types.length === 0"
              class="theme-kicker text-xs"
            >
              None
            </span>
          </dd>
        </div>

        <div class="card-version-row">
          <dt class="card-version-label">
            <Tags class="card-version-icon" />
            <span>Tags</span>
          </dt>
          <dd class="flex flex-wrap gap-1.5">
            <span
              v-for="tag in version.tags"
              :key="tag.id"
              class="theme-pill theme-pill-success px-2 py-0.5 text-xs font-semibold"
            >
              {{ tag.label }}
            </span>
            <span
              v-if="version.tags.length === 0"
              class="theme-kicker text-xs"
            >
              None
            </span>
          </dd>
        </div>

        <div class="card-version-row">
          <dt class="card-version-label">
            <KeyRound class="card-version-icon" />
            <span>Keywords</span>
          </dt>
          <dd class="flex flex-wrap gap-1.5">
            <span
              v-for="keyword in version.keywords"
              :key="`keyword-${keyword}`"
              class="theme-pill theme-pill-keyword px-2 py-0.5 text-xs"
            >
              {{ keyword }}
            </span>
            <span
              v-if="version.keywords.length === 0"
              class="theme-kicker text-xs"
            >
              None
            </span>
          </dd>
        </div>

        <div class="card-version-row">
          <dt class="card-version-label">
            <Hash class="card-version-icon" />
            <span>Symbols</span>
          </dt>
          <dd class="flex flex-wrap gap-1.5">
            <span
              v-for="symbol in version.symbols"
              :key="symbol.id"
              class="theme-pill theme-pill-symbol px-2 py-0.5 text-xs"
            >
              {{ symbol.label }}
            </span>
            <span
              v-if="version.symbols.length === 0"
              class="theme-kicker text-xs"
            >
              None
            </span>
          </dd>
        </div>
      </dl>
    </section>
  </div>
</template>

<script setup lang="ts">
import CardMarkupText from '@/domain/cards/components/CardMarkupText.vue';
import { BookOpenText, Flag, Hash, HeartPulse, KeyRound, ScrollText, Sparkles, Swords, Tags } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import SymbolizedText from '@/domain/cards/components/SymbolizedText.vue';
import { formatCardContentVersion, type CardGroupSummary, type CardVersionDetail, type SymbolLookupMap } from '@/domain/cards/types';
import { buildCardGroupDetailLocation } from '@/domain/cards/utils/gallery/galleryNavigation';

const route = useRoute();

withDefaults(defineProps<{
  version: CardVersionDetail;
  symbolByKey: SymbolLookupMap;
  toAbsoluteApiUrl: (urlPath: string) => string;
  canFlag?: boolean;
  cardGroups?: CardGroupSummary[];
}>(), {
  canFlag: false,
  cardGroups: () => [],
});

defineEmits<{
  (e: 'flag-parse-issue'): void;
}>();
</script>

<style scoped>
/* The printing lies on the table: printed-card corners and a soft shadow from the lamp above. */
.card-version-art {
  border-radius: 4.5% / 3.2%;
  box-shadow:
    0 2px 4px rgba(4, 6, 18, 0.12),
    0 18px 40px -18px rgba(4, 6, 18, 0.45);
}

.card-version-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-soft);
}

.card-version-icon {
  height: 0.875rem;
  width: 0.875rem;
  flex-shrink: 0;
  color: var(--accent);
}

.card-version-stat {
  padding: 0.875rem 1rem;
}

.card-version-stat + .card-version-stat {
  border-left: 1px solid var(--color-border);
}

.card-version-stat:first-child {
  padding-left: 0;
}

.card-version-rules {
  border-left: 2px solid color-mix(in srgb, var(--accent) 55%, transparent);
  padding: 0.25rem 0 0.25rem 1rem;
  line-height: 1.65;
}

.card-version-row {
  display: grid;
  grid-template-columns: 8rem minmax(0, 1fr);
  align-items: baseline;
  gap: 1rem;
  padding: 0.75rem 0;
}
</style>
