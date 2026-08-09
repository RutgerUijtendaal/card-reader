<template>
  <Teleport
    to="#app-page-header-outlet"
    :disabled="!hasShellHeaderOutlet"
  >
    <header
      class="theme-page-header border-b"
      :style="headerStyle"
    >
      <div
        class="flex flex-col gap-4 px-5 py-5"
        :class="[
          topRowClass,
          hasCenterContent
            ? 'lg:grid lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] lg:items-center'
            : 'lg:flex-row lg:items-stretch lg:justify-between',
        ]"
      >
        <div
          class="app-page-header-primary flex min-w-0 flex-1 gap-3"
          :class="hasSupportingContent ? 'items-start' : 'items-center'"
        >
          <div class="theme-card-frame-muted theme-section-title flex h-12 w-12 shrink-0 items-center justify-center rounded-xl">
            <component
              :is="icon"
              class="h-5 w-5"
            />
          </div>

          <div class="min-w-0">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <component
                :is="titleTag"
                class="theme-section-title truncate font-semibold"
                :class="titleClass"
              >
                {{ title }}
              </component>

              <slot name="titleMeta" />
            </div>

            <div
              v-if="hasSubtitleContent"
              class="theme-section-muted mt-1"
              :class="subtitleClass"
            >
              <slot name="subtitle">
                {{ subtitle }}
              </slot>
            </div>

            <div
              v-if="$slots.details"
              class="mt-3"
            >
              <slot name="details" />
            </div>
          </div>
        </div>

        <div
          v-if="hasCenterContent"
          class="app-page-header-center flex min-w-0 justify-center"
        >
          <slot name="center" />
        </div>

        <div
          v-if="hasHeaderActions"
          class="lg:flex lg:self-stretch lg:items-center lg:justify-end lg:justify-self-end"
        >
          <div class="flex flex-wrap items-center gap-2 lg:justify-end">
            <AppHeaderAction
              v-if="hasBackLink"
              :icon="ArrowLeft"
              :label="backLabel"
              short-label="Back"
              :to="resolvedBackTo"
            />
            <slot name="actions" />
          </div>
        </div>
      </div>

      <div
        v-if="hasBottomRow"
        class="theme-divider theme-subheader-row flex flex-wrap items-center gap-3 border-t px-5 py-4"
        :class="[bottomRowClass, bottomRowLayoutClass]"
        :style="bottomRowStyle"
      >
        <div
          v-if="hasBottomLeft"
          class="flex flex-wrap items-center gap-2"
        >
          <slot name="bottomLeft" />
        </div>

        <div
          v-if="hasBottomRight"
          class="ml-auto lg:flex lg:self-stretch lg:items-center lg:justify-end"
        >
          <div class="flex flex-wrap items-center gap-2 lg:justify-end">
            <slot name="bottomRight" />
          </div>
        </div>
      </div>
    </header>
  </Teleport>
</template>

<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next';
import { Comment, computed, onMounted, ref, useSlots } from 'vue';
import type { Component } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import AppHeaderAction from '@/shared/components/app/AppHeaderAction.vue';

const props = withDefaults(
  defineProps<{
    icon: Component;
    title: string;
    subtitle?: string;
    backTo?: RouteLocationRaw | null;
    backLabel?: string;
    titleTag?: 'h1' | 'h2' | 'h3';
    titleClass?: string;
    subtitleClass?: string;
  }>(),
  {
    titleTag: 'h1',
    titleClass: 'text-xl',
    subtitle: '',
    subtitleClass: 'text-sm',
    backTo: null,
    backLabel: '',
  },
);

const slots = useSlots();
const hasShellHeaderOutlet = ref(false);
const hasRenderableSlot = (
  name: 'actions' | 'bottomLeft' | 'bottomRight' | 'center' | 'details' | 'subtitle' | 'titleMeta',
): boolean => {
  const slot = slots[name];
  if (!slot) {
    return false;
  }
  return slot().some((node) => node.type !== Comment);
};
const hasBackLink = computed(() => Boolean(props.backTo && props.backLabel));
const hasSubtitle = computed(() => props.subtitle.trim().length > 0);
const hasSubtitleContent = computed(() => hasSubtitle.value || hasRenderableSlot('subtitle'));
const hasSupportingContent = computed(() => hasSubtitleContent.value || hasRenderableSlot('details'));
const hasHeaderActions = computed(() => hasBackLink.value || hasRenderableSlot('actions'));
const hasCenterContent = computed(() => hasRenderableSlot('center'));
const hasBottomLeft = computed(() => hasRenderableSlot('bottomLeft'));
const hasBottomRight = computed(() => hasRenderableSlot('bottomRight'));
const hasBottomRow = computed(() => hasBottomLeft.value || hasBottomRight.value);
const bottomRowLayoutClass = computed(() => {
  if (hasBottomLeft.value && hasBottomRight.value) {
    return 'justify-between';
  }

  if (hasBottomRight.value) {
    return 'justify-end';
  }

  return 'justify-start';
});
const resolvedBackTo = computed<RouteLocationRaw>(() => props.backTo ?? '/');
const headerStyle = computed(() => ({
  borderColor: 'color-mix(in srgb, var(--color-border-strong) 48%, transparent)',
  background: [
    'linear-gradient(180deg,',
    'color-mix(in srgb, var(--color-surface-strong) 72%, transparent) 0%,',
    'color-mix(in srgb, var(--color-surface) 42%, transparent) 100%)',
  ].join(' '),
  backdropFilter: 'blur(24px) saturate(1.45)',
  WebkitBackdropFilter: 'blur(24px) saturate(1.45)',
  color: 'var(--color-text)',
  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.18), 0 1px 0 rgba(148,163,184,0.2), 0 14px 38px rgba(15,23,42,0.14)',
}));
const bottomRowStyle = computed(() => ({
  background: 'color-mix(in srgb, var(--color-surface) 34%, transparent)',
  backdropFilter: 'blur(20px) saturate(1.35)',
  WebkitBackdropFilter: 'blur(20px) saturate(1.35)',
}));
const topRowClass = computed(() => []);
const bottomRowClass = computed(() => '');

onMounted(() => {
  hasShellHeaderOutlet.value = document.getElementById('app-page-header-outlet') !== null;
});
</script>
