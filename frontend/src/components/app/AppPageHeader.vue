<template>
  <header
    class="rounded-xl border backdrop-blur-sm"
    :style="headerStyle"
  >
    <div
      class="flex flex-col gap-4 px-5 py-5 lg:flex-row lg:items-stretch lg:justify-between"
      :class="topRowClass"
    >
      <div class="flex min-w-0 flex-1 items-start gap-3">
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

          <p
            class="theme-section-muted mt-1"
            :class="subtitleClass"
          >
            {{ subtitle }}
          </p>

          <div
            v-if="$slots.details"
            class="mt-3"
          >
            <slot name="details" />
          </div>
        </div>
      </div>

      <div
        v-if="hasHeaderActions"
        class="lg:flex lg:self-stretch lg:items-center lg:justify-end"
      >
        <div class="flex flex-wrap items-center gap-2 lg:justify-end">
          <RouterLink
            v-if="hasBackLink"
            class="btn-secondary inline-flex items-center gap-2"
            :to="resolvedBackTo"
          >
            <ArrowLeft class="h-4 w-4" />
            <span>{{ backLabel }}</span>
          </RouterLink>
          <slot name="actions" />
        </div>
      </div>
    </div>

    <div
      v-if="$slots.bottomRight"
      class="theme-divider theme-subheader-row flex justify-end border-t px-5 py-4"
      :class="bottomRowClass"
    >
      <div class="lg:flex lg:self-stretch lg:items-center lg:justify-end">
        <div class="flex flex-wrap items-center gap-2 lg:justify-end">
          <slot name="bottomRight" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next';
import { computed, useSlots } from 'vue';
import { RouterLink } from 'vue-router';
import type { Component } from 'vue';
import type { RouteLocationRaw } from 'vue-router';

const props = withDefaults(
  defineProps<{
    icon: Component;
    title: string;
    subtitle: string;
    backTo?: RouteLocationRaw | null;
    backLabel?: string;
    titleTag?: 'h1' | 'h2' | 'h3';
    titleClass?: string;
    subtitleClass?: string;
  }>(),
  {
    titleTag: 'h1',
    titleClass: 'text-2xl',
    subtitleClass: 'text-sm',
    backTo: null,
    backLabel: '',
  },
);

const slots = useSlots();
const hasBackLink = computed(() => Boolean(props.backTo && props.backLabel));
const hasHeaderActions = computed(() => hasBackLink.value || Boolean(slots.actions));
const hasBottomRow = computed(() => Boolean(slots.bottomRight));
const resolvedBackTo = computed<RouteLocationRaw>(() => props.backTo ?? '/');
const headerStyle = computed(() => ({
  borderColor: 'var(--color-border)',
  background: 'var(--color-surface)',
  color: 'var(--color-text)',
}));
const topRowClass = computed(() => [
  'bg-[var(--color-surface)]',
  hasBottomRow.value ? 'rounded-t-xl' : 'rounded-xl',
]);
const bottomRowClass = computed(() => 'bg-[var(--color-surface)] rounded-b-xl');
</script>
