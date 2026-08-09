<template>
  <component
    :is="to ? RouterLink : 'button'"
    :to="to"
    :type="to ? undefined : 'button'"
    class="block w-full rounded-lg border px-3 py-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-input-focus)]"
    :class="itemClass"
    :aria-current="active ? 'page' : undefined"
    :aria-disabled="disabled || undefined"
    :disabled="to ? undefined : disabled"
    :tabindex="to && disabled ? -1 : undefined"
    @click="handleClick"
  >
    <div class="flex items-start gap-3">
      <component
        :is="icon"
        v-if="icon"
        class="mt-0.5 h-4 w-4 shrink-0"
        :class="iconClass"
        aria-hidden="true"
      />
      <span class="min-w-0 flex-1">
        <span class="flex min-w-0 items-start justify-between gap-3">
          <span class="min-w-0 truncate text-sm font-semibold">{{ label }}</span>
          <slot name="trailing" />
        </span>
        <span
          v-if="description"
          class="mt-1 block truncate text-xs"
          :class="active ? 'theme-section-title' : 'theme-section-muted'"
        >
          {{ description }}
        </span>
      </span>
    </div>

    <div
      v-if="$slots.meta"
      class="mt-3"
    >
      <slot name="meta" />
    </div>
  </component>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue';
import { RouterLink, type RouteLocationRaw } from 'vue-router';

const props = withDefaults(
  defineProps<{
    label: string;
    description?: string;
    icon?: Component;
    iconClass?: string;
    to?: RouteLocationRaw;
    active?: boolean;
    disabled?: boolean;
  }>(),
  {
    description: '',
    icon: undefined,
    iconClass: '',
    to: undefined,
    active: false,
    disabled: false,
  },
);

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const itemClass = computed(() => [
  props.active
    ? 'theme-selected-surface-strong'
    : 'theme-card-frame theme-section-title hover:border-[var(--color-border-strong)]',
  props.disabled ? 'theme-disabled cursor-not-allowed' : '',
]);

const handleClick = (event: MouseEvent): void => {
  if (props.disabled) {
    event.preventDefault();
    return;
  }
  emit('click', event);
};
</script>
