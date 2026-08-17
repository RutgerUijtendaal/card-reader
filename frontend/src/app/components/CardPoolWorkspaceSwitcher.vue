<template>
  <div
    class="w-full"
    data-testid="card-pool-workspace-switcher"
  >
    <div
      class="theme-card-frame-muted flex gap-1 rounded-xl p-1"
      :class="collapsed ? 'mx-auto w-fit flex-col items-center' : 'w-full'"
      role="group"
      aria-label="Card workspace"
    >
      <InfoTooltip
        v-for="option in workspace.availableOptions"
        :key="option.value"
        v-slot="{ tooltipId }"
        :text="option.label"
        :placement="collapsed ? 'right' : 'top'"
        :trigger-tabbable="false"
        :trigger-class="collapsed ? '' : 'min-w-0 flex-1'"
      >
        <button
          type="button"
          class="inline-flex items-center justify-center rounded-lg transition"
          :class="[
            collapsed ? 'h-10 w-10' : 'h-12 w-full',
            workspace.activePool === option.value ? 'theme-selected-surface-strong' : 'theme-section-muted hover:theme-card-frame',
          ]"
          :aria-label="`${option.label} workspace`"
          :aria-describedby="tooltipId"
          :aria-pressed="workspace.activePool === option.value"
          :data-card-pool="option.value"
          @click="void selectPool(option.value)"
        >
          <component
            :is="CARD_POOL_ICONS[option.value]"
            :class="collapsed ? 'h-5 w-5' : 'h-7 w-7'"
            aria-hidden="true"
          />
        </button>
      </InfoTooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useCardPoolWorkspaceSelection } from '@/app/composables/useCardPoolWorkspaceSelection';
import type { CardPool } from '@/domain/cards/cardPools';
import { CARD_POOL_ICONS } from '@/domain/cards/cardPoolIcons';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';

withDefaults(defineProps<{ collapsed?: boolean }>(), {
  collapsed: false,
});
const emit = defineEmits<{ selected: [] }>();
const workspace = useCardPoolWorkspaceStore();
const workspaceSelection = useCardPoolWorkspaceSelection();

const selectPool = async (cardPool: CardPool): Promise<void> => {
  const selected = await workspaceSelection.selectPool(cardPool);
  if (!selected) {
    return;
  }
  emit('selected');
};
</script>
