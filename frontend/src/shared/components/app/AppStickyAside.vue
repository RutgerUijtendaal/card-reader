<template>
  <aside
    class="app-sticky-aside"
    :class="[side === 'right' ? 'app-sticky-aside-right' : 'app-sticky-aside-left', rootClass]"
  >
    <div
      class="app-sticky-aside-scroll app-scrollbar"
      :class="scrollClass"
    >
      <slot />
    </div>
    <div
      v-if="$slots.footer && footerVisible"
      class="app-sticky-aside-footer theme-divider mt-4 shrink-0 border-t pt-4"
      :class="footerClass"
    >
      <slot name="footer" />
    </div>
  </aside>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    side?: 'left' | 'right';
    rootClass?: string;
    scrollClass?: string;
    footerClass?: string;
    footerVisible?: boolean;
  }>(),
  {
    side: 'left',
    rootClass: '',
    scrollClass: '',
    footerClass: '',
    footerVisible: true,
  },
);
</script>
