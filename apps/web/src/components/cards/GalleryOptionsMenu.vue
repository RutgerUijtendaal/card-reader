<template>
  <div>
    <button
      ref="triggerRef"
      type="button"
      class="btn-secondary inline-flex items-center gap-2 whitespace-nowrap"
      @click="toggle"
    >
      <SlidersHorizontal class="h-4 w-4" />
      <span>Gallery Options</span>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="z-30 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-xl"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-4">
          <label class="flex items-start justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900">
                Tooltip
              </p>
              <p class="text-xs text-slate-500">
                Show card details on hover in the gallery.
              </p>
            </div>
            <input
              :checked="tooltipEnabled"
              type="checkbox"
              class="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600"
              @change="$emit('update:tooltipEnabled', ($event.target as HTMLInputElement).checked)"
            >
          </label>

          <label class="block space-y-2">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">
                  Card Size
                </p>
                <p class="text-xs text-slate-500">
                  Scale gallery cards within a practical range.
                </p>
              </div>
              <span class="text-xs font-medium text-slate-500">
                {{ percentLabel }}
              </span>
            </div>
            <input
              :value="cardScale"
              type="range"
              min="0.8"
              max="1.2"
              step="0.05"
              class="w-full accent-sky-600"
              @input="$emit('update:cardScale', Number(($event.target as HTMLInputElement).value))"
            >
          </label>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SlidersHorizontal } from 'lucide-vue-next';
import { useFloatingPopover } from '@/composables/useFloatingPopover';

const props = defineProps<{
  tooltipEnabled: boolean;
  cardScale: number;
}>();

defineEmits<{
  (e: 'update:tooltipEnabled', value: boolean): void;
  (e: 'update:cardScale', value: number): void;
}>();

const { isOpen, triggerRef, panelRef, x, y, toggle } = useFloatingPopover({
  placement: 'bottom-start',
});
const percentLabel = computed(() => `${Math.round(props.cardScale * 100)}%`);
</script>
