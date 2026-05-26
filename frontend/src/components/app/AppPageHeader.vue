<template>
  <header
    class="page-card flex flex-col gap-6"
    :class="cardClass"
  >
    <div
      class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"
    >
      <div class="min-w-0 flex-1">
        <RouterLink
          v-if="hasBackLink"
          class="btn-secondary inline-flex w-fit items-center gap-2"
          :to="resolvedBackTo"
        >
          <ArrowLeft class="h-4 w-4" />
          <span>{{ backLabel }}</span>
        </RouterLink>
        <div
          v-else
          class="flex min-w-0 items-start gap-3"
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
      </div>

      <div
        v-if="$slots.actions"
        class="flex flex-wrap gap-2 lg:shrink-0 lg:justify-end"
      >
        <slot name="actions" />
      </div>
    </div>

    <div
      v-if="hasBackLink || $slots.bottomRight"
      class="flex flex-col gap-4 lg:flex-row lg:items-stretch lg:justify-between"
    >
      <div
        v-if="hasBackLink"
        class="min-w-0 flex flex-1 items-start gap-3"
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
        v-if="$slots.bottomRight"
        class="lg:flex lg:self-stretch lg:items-center lg:justify-end"
      >
        <div class="flex flex-wrap items-center gap-2 lg:justify-end">
          <slot name="bottomRight" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ArrowLeft } from 'lucide-vue-next';
import { computed } from 'vue';
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
    cardClass?: string;
    titleClass?: string;
    subtitleClass?: string;
  }>(),
  {
    titleTag: 'h1',
    cardClass: '',
    titleClass: 'text-2xl',
    subtitleClass: 'text-sm',
    backTo: null,
    backLabel: '',
  },
);

const hasBackLink = computed(() => Boolean(props.backTo && props.backLabel));
const resolvedBackTo = computed<RouteLocationRaw>(() => props.backTo ?? '/');
</script>
