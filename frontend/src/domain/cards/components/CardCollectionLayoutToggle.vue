<template>
  <div
    class="card-layout-toggle"
    role="group"
    aria-label="Card layout"
  >
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="card-layout-toggle-button"
      :class="{ 'card-layout-toggle-button-active': modelValue === option.value }"
      :aria-pressed="modelValue === option.value"
      :aria-label="option.label"
      :title="option.label"
      @click="emit('update:modelValue', option.value)"
    >
      <component
        :is="option.icon"
        class="h-4 w-4"
        aria-hidden="true"
      />
    </button>
  </div>
</template>

<script setup lang="ts">
import { LayoutGrid, List } from 'lucide-vue-next';
import type { CardCollectionLayout } from '@/domain/cards/composables/useCardCollectionLayout';

defineProps<{ modelValue: CardCollectionLayout }>();
const emit = defineEmits<{ 'update:modelValue': [value: CardCollectionLayout] }>();

const options = [
  { value: 'list' as const, label: 'Show as a list', icon: List },
  { value: 'images' as const, label: 'Show card images', icon: LayoutGrid },
];
</script>

<style scoped>
.card-layout-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
}

.card-layout-toggle-button {
  display: inline-flex;
  height: 2rem;
  width: 2rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  color: var(--color-text-muted);
  transition:
    background-color 120ms ease,
    color 120ms ease;
}

.card-layout-toggle-button:hover {
  background: var(--color-surface-soft);
  color: var(--color-text);
}

.card-layout-toggle-button-active,
.card-layout-toggle-button-active:hover {
  background: color-mix(in srgb, var(--accent) 16%, transparent);
  color: var(--accent);
}

.card-layout-toggle-button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--accent);
}
</style>
