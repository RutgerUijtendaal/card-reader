<template>
  <div
    class="w-full"
  >
    <label
      v-if="collapsed"
      class="block"
    >
      <span class="sr-only">Card workspace</span>
      <select
        :value="workspace.activePool"
        class="input-base h-10 w-full px-1 text-center text-xs font-semibold"
        aria-label="Card workspace"
        :title="`${cardPoolLabel(workspace.activePool)} workspace`"
        @change="selectFromEvent"
      >
        <option
          v-for="option in workspace.availableOptions"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>
    </label>

    <div
      v-else
      class="theme-card-frame-muted grid gap-1 rounded-xl p-1"
      :style="{ gridTemplateColumns: `repeat(${workspace.availableOptions.length}, minmax(0, 1fr))` }"
      role="group"
      aria-label="Card workspace"
    >
      <button
        v-for="option in workspace.availableOptions"
        :key="option.value"
        type="button"
        class="rounded-lg px-2 py-2 text-xs font-semibold transition"
        :class="workspace.activePool === option.value ? 'theme-selected-surface-strong' : 'theme-section-muted hover:theme-card-frame'"
        :aria-pressed="workspace.activePool === option.value"
        @click="selectPool(option.value)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { cardPoolLabel, isCardPool, type CardPool } from '@/domain/cards/cardPools';
import {
  buildWorkspaceGalleryLocation,
  useCardPoolWorkspaceStore,
} from '@/domain/cards/cardPoolWorkspace';

withDefaults(defineProps<{ collapsed?: boolean }>(), {
  collapsed: false,
});
const emit = defineEmits<{ selected: [] }>();
const router = useRouter();
const workspace = useCardPoolWorkspaceStore();

const selectPool = (cardPool: CardPool): void => {
  workspace.selectPool(cardPool);
  emit('selected');
  void router.push(buildWorkspaceGalleryLocation(cardPool));
};

const selectFromEvent = (event: Event): void => {
  const value = (event.target as HTMLSelectElement).value;
  if (isCardPool(value)) {
    selectPool(value);
  }
};
</script>
