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
          @click="selectPool(option.value)"
        >
          <component
            :is="poolIcons[option.value]"
            :class="collapsed ? 'h-5 w-5' : 'h-7 w-7'"
            aria-hidden="true"
          />
        </button>
      </InfoTooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Scale, Shield } from 'lucide-vue-next';
import { useRouter } from 'vue-router';
import type { Component } from 'vue';
import type { CardPool } from '@/domain/cards/cardPools';
import EvilPoolIcon from '@/domain/cards/components/EvilPoolIcon.vue';
import {
  buildWorkspaceGalleryLocation,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';

withDefaults(defineProps<{ collapsed?: boolean }>(), {
  collapsed: false,
});
const emit = defineEmits<{ selected: [] }>();
const router = useRouter();
const workspace = useCardPoolWorkspaceStore();
const poolIcons: Record<CardPool, Component> = {
  player: Shield,
  evil: EvilPoolIcon,
  neutral: Scale,
};

const selectPool = (cardPool: CardPool): void => {
  workspace.selectPool(cardPool);
  emit('selected');
  void router.push(buildWorkspaceGalleryLocation(cardPool));
};
</script>
