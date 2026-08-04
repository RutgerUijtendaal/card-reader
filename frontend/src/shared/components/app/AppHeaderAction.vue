<template>
  <InfoTooltip
    v-slot="{ tooltipId }"
    :text="label"
    :placement="tooltipPlacement"
    :trigger-tabbable="false"
  >
    <RouterLink
      v-if="to"
      :to="to"
      :class="actionClass"
      :aria-label="label"
      :aria-describedby="tooltipId"
      :aria-current="variant === 'tab' && active ? 'page' : undefined"
      :aria-disabled="disabled || undefined"
      :tabindex="disabled ? -1 : undefined"
      @click="handleClick"
    >
      <component
        :is="icon"
        class="h-4 w-4 shrink-0"
        :class="iconClass"
        aria-hidden="true"
      />
      <span>{{ shortLabel }}</span>
      <slot name="trailing" />
    </RouterLink>
    <button
      v-else
      :class="actionClass"
      type="button"
      :aria-label="label"
      :aria-describedby="tooltipId"
      :aria-pressed="variant === 'tab' ? active : undefined"
      :disabled="disabled"
      @click="handleClick"
    >
      <component
        :is="icon"
        class="h-4 w-4 shrink-0"
        :class="iconClass"
        aria-hidden="true"
      />
      <span>{{ shortLabel }}</span>
      <slot name="trailing" />
    </button>
  </InfoTooltip>
</template>

<script setup lang="ts">
import type { Placement } from '@floating-ui/vue';
import type { Component } from 'vue';
import { computed } from 'vue';
import { RouterLink, type RouteLocationRaw } from 'vue-router';
import InfoTooltip from '@/shared/components/InfoTooltip.vue';

const props = withDefaults(
  defineProps<{
    icon: Component;
    label: string;
    shortLabel: string;
    to?: RouteLocationRaw;
    variant?: 'primary' | 'secondary' | 'tab';
    tooltipPlacement?: Placement;
    disabled?: boolean;
    active?: boolean;
    iconClass?: string;
  }>(),
  {
    to: undefined,
    variant: 'secondary',
    tooltipPlacement: 'bottom',
    disabled: false,
    active: false,
    iconClass: '',
  },
);

const emit = defineEmits<{
  click: [event: MouseEvent];
}>();

const actionClass = computed(() => [
  'app-header-action h-10 w-auto shrink-0 gap-2 px-3',
  props.variant === 'tab'
    ? ['theme-tab', props.active ? 'theme-tab-active' : '']
    : props.variant === 'primary'
      ? 'btn-primary'
      : 'btn-secondary',
]);

const handleClick = (event: MouseEvent): void => {
  if (props.disabled) {
    event.preventDefault();
    return;
  }
  emit('click', event);
};
</script>
