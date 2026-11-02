<template>
  <div>
    <div
      :id="contentId"
      class="app-read-more relative overflow-hidden"
      :style="collapsed ? { maxHeight: collapsedHeight } : undefined"
    >
      <div ref="contentRef">
        <slot />
      </div>
      <div
        v-if="collapsed"
        class="app-read-more-fade pointer-events-none absolute inset-x-0 bottom-0 h-12"
        aria-hidden="true"
      />
    </div>
    <button
      v-if="overflowing"
      type="button"
      class="theme-link mt-2 text-sm font-semibold"
      :aria-expanded="expanded"
      :aria-controls="contentId"
      @click="expanded = !expanded"
    >
      {{ expanded ? 'Show less' : 'Read more' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue';
import { useResizeObserver } from '@vueuse/core';

/** Shows long prose at a fixed height first, with a toggle once the text is taller than that. */
const props = withDefaults(defineProps<{ collapsedHeight?: string }>(), {
  collapsedHeight: '10rem',
});

const contentId = useId();
const contentRef = ref<HTMLElement | null>(null);
const expanded = ref(false);
const overflowing = ref(false);
const collapsed = computed(() => overflowing.value && !expanded.value);

const measure = (): void => {
  const element = contentRef.value;
  if (!element) {
    return;
  }
  const rootFontSize = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const limitPx = Number.parseFloat(props.collapsedHeight) * (props.collapsedHeight.endsWith('rem') ? rootFontSize : 1);
  overflowing.value = element.scrollHeight > limitPx + 1;
};

useResizeObserver(contentRef, measure);
</script>

<style scoped>
.app-read-more-fade {
  background: linear-gradient(180deg, transparent 0%, var(--table-canvas) 100%);
}
</style>
