<template>
  <div class="pointer-events-none absolute inset-0">
    <div
      v-for="region in regions"
      :key="region.region_id"
      class="absolute flex items-center justify-center overflow-hidden rounded-md border-2 shadow-[0_0_0_1px_rgba(15,23,42,0.45)] backdrop-blur-[4px]"
      :class="regionClass(region.parser_type)"
      :style="{
        left: `${region.left_pct}%`,
        top: `${region.top_pct}%`,
        width: `${region.width_pct}%`,
        height: `${region.height_pct}%`,
      }"
    >
      <span class="max-w-full px-2 text-center font-semibold leading-none text-slate-950 [font-size:clamp(0.65rem,1.2vw,0.95rem)] [text-shadow:0_1px_1px_rgba(255,255,255,0.35)]">
        {{ region.region_id }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TemplatePreviewRenderRegion } from '@/features/admin/types';
import type { TemplateParserType } from '@/domain/templates/parserTypes';

defineProps<{
  regions: TemplatePreviewRenderRegion[];
}>();

const REGION_CLASSES = {
  name: 'border-cyan-300 bg-cyan-500/10 text-white',
  name_mana_cost: 'border-sky-300 bg-sky-500/10 text-white',
  type_tag: 'border-emerald-300 bg-emerald-500/10 text-white',
  rules_text: 'border-amber-300 bg-amber-500/10 text-white',
  attack: 'border-rose-300 bg-rose-500/10 text-white',
  health: 'border-orange-300 bg-orange-500/10 text-white',
  affinity: 'border-violet-300 bg-violet-500/10 text-white',
} as const satisfies Readonly<Record<TemplateParserType, string>>;

const regionClass = (parserType: TemplateParserType): string => REGION_CLASSES[parserType];
</script>
