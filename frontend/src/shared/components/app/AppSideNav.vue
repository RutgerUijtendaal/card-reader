<template>
  <section class="space-y-4">
    <div class="px-1">
      <h3 class="theme-section-title text-sm font-semibold">
        {{ title }}
      </h3>
      <p
        v-if="description"
        class="theme-section-muted mt-1 text-xs leading-5"
      >
        {{ description }}
      </p>
    </div>

    <slot name="before" />
    <slot name="mobile" />

    <nav
      :class="listClass"
      :aria-label="navigationLabel"
    >
      <slot />
    </nav>

    <slot name="after" />
  </section>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title: string;
    description?: string;
    navigationLabel: string;
    listClass?: string;
  }>(),
  {
    description: '',
    listClass: 'flex flex-col gap-2',
  },
);
</script>
