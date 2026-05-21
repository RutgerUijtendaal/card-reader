<template>
  <div class="pointer-events-none absolute inset-0">
    <div
      v-for="region in regions"
      :key="region.region_id"
      class="absolute flex items-center justify-center overflow-hidden rounded-md border-2 shadow-[0_0_0_1px_rgba(15,23,42,0.45)] backdrop-blur-[1.5px]"
      :class="regionClass(region.parser_type)"
      :style="{
        left: `${region.left_pct}%`,
        top: `${region.top_pct}%`,
        width: `${region.width_pct}%`,
        height: `${region.height_pct}%`,
      }"
    >
      <span class="max-w-full px-2 text-center text-[11px] font-semibold leading-none text-slate-950 [text-shadow:0_1px_1px_rgba(255,255,255,0.35)]">
        {{ region.region_id }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TemplateParserType, TemplatePreviewRenderRegion } from '@/modules/settings/types';

defineProps<{
  regions: TemplatePreviewRenderRegion[];
}>();

const regionClass = (parserType: TemplateParserType): string => {
  if (parserType === 'name_mana_cost') {
    return 'border-sky-300 bg-sky-500/10 text-white';
  }
  if (parserType === 'type_tag') {
    return 'border-emerald-300 bg-emerald-500/10 text-white';
  }
  if (parserType === 'rules_text') {
    return 'border-amber-300 bg-amber-500/10 text-white';
  }
  if (parserType === 'attack') {
    return 'border-rose-300 bg-rose-500/10 text-white';
  }
  if (parserType === 'health') {
    return 'border-orange-300 bg-orange-500/10 text-white';
  }
  return 'border-violet-300 bg-violet-500/10 text-white';
};
</script>
