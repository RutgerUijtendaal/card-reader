<template>
  <div
    class="w-full"
    data-testid="card-pool-workspace-switcher"
  >
    <div
      v-if="collapsed"
      class="workspace-switcher-rail mx-auto flex w-fit flex-col items-center gap-1 rounded-lg p-1"
      role="group"
      aria-label="Card workspace"
    >
      <InfoTooltip
        v-for="option in workspace.availableOptions"
        :key="option.value"
        v-slot="{ tooltipId }"
        :text="option.label"
        placement="right"
        :trigger-tabbable="false"
      >
        <button
          type="button"
          class="workspace-switcher-option inline-flex h-10 w-10 items-center justify-center rounded-md transition"
          :class="workspace.activePool === option.value ? 'workspace-switcher-option-active' : ''"
          :aria-label="`${option.label} workspace`"
          :aria-describedby="tooltipId"
          :aria-pressed="workspace.activePool === option.value"
          :data-card-pool="option.value"
          @click="void selectPool(option.value)"
        >
          <component
            :is="CARD_POOL_ICONS[option.value]"
            class="h-5 w-5"
            aria-hidden="true"
          />
        </button>
      </InfoTooltip>
    </div>

    <div
      v-else
      class="workspace-switcher-tabs flex w-full"
      role="group"
      aria-label="Card workspace"
    >
      <button
        v-for="option in workspace.availableOptions"
        :key="option.value"
        type="button"
        class="workspace-switcher-tab inline-flex h-10 min-w-0 flex-1 items-center justify-center gap-1.5 px-1 text-[13px] font-medium transition"
        :class="workspace.activePool === option.value ? 'workspace-switcher-tab-active' : ''"
        :aria-label="`${option.label} workspace`"
        :aria-pressed="workspace.activePool === option.value"
        :data-card-pool="option.value"
        @click="void selectPool(option.value)"
      >
        <component
          :is="CARD_POOL_ICONS[option.value]"
          class="h-4 w-4 shrink-0"
          aria-hidden="true"
        />
        <span class="truncate">{{ option.label }}</span>
      </button>
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

<style scoped>
/* Expanded: a quiet tab row whose underline carries the active side's colour. */
.workspace-switcher-tabs {
  border-bottom: 1px solid var(--color-sidebar-border);
}

.workspace-switcher-tab {
  margin-bottom: -1px;
  border-bottom: 2px solid transparent;
  color: var(--color-nav-text);
}

.workspace-switcher-tab:hover {
  color: var(--color-nav-hover-text);
}

.workspace-switcher-tab-active,
.workspace-switcher-tab-active:hover {
  border-bottom-color: var(--sidebar-accent);
  color: #ffffff;
}

.workspace-switcher-tab-active svg {
  color: var(--sidebar-accent);
}

/* Collapsed: a compact icon rail. */
.workspace-switcher-rail {
  background: var(--color-sidebar-surface);
  box-shadow: inset 0 0 0 1px var(--color-sidebar-border);
}

.workspace-switcher-option {
  color: var(--color-nav-text);
}

.workspace-switcher-option:hover {
  background: var(--color-sidebar-surface-hover);
  color: var(--color-nav-hover-text);
}

.workspace-switcher-option-active,
.workspace-switcher-option-active:hover {
  background: color-mix(in srgb, var(--sidebar-accent) 18%, transparent);
  color: #ffffff;
}

.workspace-switcher-option-active svg {
  color: var(--sidebar-accent);
}
</style>
