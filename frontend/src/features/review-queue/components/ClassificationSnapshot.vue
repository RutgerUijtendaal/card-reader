<template>
  <div
    class="classification-snapshot py-1 pl-3"
    :class="{ 'classification-snapshot-emphasized': emphasized }"
  >
    <p class="theme-kicker text-[11px] font-medium uppercase tracking-wide">
      {{ label }}
    </p>
    <dl class="mt-2 grid gap-1 text-sm">
      <div class="flex gap-2">
        <dt class="theme-section-muted w-16 shrink-0 font-medium">
          Pool
        </dt>
        <dd>{{ cardPoolLabel(classification.card_pool) }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="theme-section-muted w-16 shrink-0 font-medium">
          Roles
        </dt>
        <dd>{{ roleLabels }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="theme-section-muted w-16 shrink-0 font-medium">
          Factions
        </dt>
        <dd>{{ factionLabels }}</dd>
      </div>
      <div class="flex gap-2">
        <dt class="theme-section-muted w-16 shrink-0 font-medium">
          Mana
        </dt>
        <dd>{{ manaLabels }}</dd>
      </div>
    </dl>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { displayCardFactionLabels } from '@/domain/cards/cardFactions';
import { displayManaFamilyLabels } from '@/domain/cards/manaFamilies';
import { cardPoolLabel } from '@/domain/cards/cardPools';
import { displayCardRoleLabels } from '@/domain/cards/cardRoles';
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
  displayCardRoleLabels(props.classification.card_roles).join(', '),
);
const factionLabels = computed(() =>
  displayCardFactionLabels(props.classification.card_factions).join(', '),
);
const manaLabels = computed(() =>
  displayManaFamilyLabels(props.classification.card_mana_families).join(', '),
);
</script>

<style scoped>
.classification-snapshot {
  border-left: 2px solid var(--color-border-strong);
  color: var(--color-text);
}

.classification-snapshot-emphasized {
  border-left-color: var(--accent);
}

.classification-snapshot-emphasized dd {
  color: var(--color-selected-text);
  font-weight: 600;
}
</style>
