<template>
  <div
    class="rounded-lg border p-3"
    :class="emphasized ? 'theme-selected-surface' : 'theme-card-frame'"
  >
    <p class="theme-kicker text-[11px] font-medium uppercase tracking-wide">
      {{ label }}
    </p>
    <dl class="mt-2 grid gap-1 text-sm">
      <div class="flex gap-2">
        <dt class="font-semibold">
          Pool
        </dt>
        <dd>{{ cardPoolLabel(classification.card_pool) }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="font-semibold">
          Roles
        </dt>
        <dd>{{ roleLabels }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="font-semibold">
          Factions
        </dt>
        <dd>{{ factionLabels }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="font-semibold">
          Mana
        </dt>
        <dd>{{ manaLabels }}</dd>
      </div>
    </dl>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cardFactionLabel } from '@/domain/cards/cardFactions';
import { manaFamilyLabel } from '@/domain/cards/manaFamilies';
import { cardPoolLabel } from '@/domain/cards/cardPools';
import { cardRoleLabel } from '@/domain/cards/cardRoles';
import type { CardClassificationSnapshot } from '@/features/review-queue/types';

const props = withDefaults(
  defineProps<{
    label: string;
    classification: CardClassificationSnapshot;
    emphasized?: boolean;
  }>(),
  { emphasized: false },
);

const roleLabels = computed(() =>
  props.classification.card_roles.length > 0
    ? props.classification.card_roles.map(cardRoleLabel).join(', ')
    : 'Normal',
);
const factionLabels = computed(() =>
  props.classification.card_factions.length > 0
    ? props.classification.card_factions.map(cardFactionLabel).join(', ')
    : 'None',
);
const manaLabels = computed(() =>
  props.classification.card_mana_families.length > 0
    ? props.classification.card_mana_families.map(manaFamilyLabel).join(', ')
    : 'Colorless',
);
</script>
