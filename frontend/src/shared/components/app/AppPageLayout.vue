<template>
  <section
    class="app-page-layout"
    :class="[layoutClass, rootClass]"
  >
    <slot name="aside" />
    <section
      class="app-page-layout-main"
      :class="mainClass"
    >
      <slot />
    </section>
    <slot name="endAside" />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    columns?: 'one' | 'sidebar' | 'three';
    rootClass?: string;
    mainClass?: string;
  }>(),
  {
    columns: 'sidebar',
    rootClass: '',
    mainClass: '',
  },
);

const layoutClass = computed(() => `app-page-layout-${props.columns}`);
</script>
