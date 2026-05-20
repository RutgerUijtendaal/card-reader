<template>
  <div class="relative">
    <button
      ref="triggerRef"
      type="button"
      class="theme-mode-button"
      :title="buttonTitle"
      aria-label="Open theme menu"
      @click="toggle"
    >
      <span class="theme-mode-icon-wrap">
        <component
          :is="activeIcon"
          class="h-4 w-4"
        />
      </span>
      <span class="min-w-0 flex-1 text-left">
        <span class="block text-sm font-semibold">Theme</span>
        <span class="block text-xs opacity-75">{{ activeLabel }}</span>
      </span>
      <ChevronDown
        class="h-4 w-4 shrink-0 transition"
        :class="isOpen ? 'rotate-180' : ''"
      />
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        ref="panelRef"
        class="theme-popover z-50 w-[19rem]"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
      >
        <div class="space-y-2">
          <button
            v-for="option in options"
            :key="option.value"
            type="button"
            class="theme-mode-option"
            :class="preference === option.value ? 'theme-mode-option-active' : ''"
            @click="selectTheme(option.value)"
          >
            <span class="theme-mode-option-icon">
              <component
                :is="option.icon"
                class="h-4 w-4"
              />
            </span>
            <span class="min-w-0 flex-1 text-left">
              <span class="block text-sm font-semibold">{{ option.label }}</span>
              <span class="block text-xs opacity-70">{{ option.description }}</span>
            </span>
            <span
              v-if="preference === option.value"
              class="text-xs font-semibold"
            >
              Active
            </span>
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ChevronDown, LaptopMinimal, MoonStar, SunMedium } from 'lucide-vue-next';
import { useFloatingPopover } from '@/composables/useFloatingPopover';
import { useTheme, type ThemePreference } from '@/composables/useTheme';

const { preference, resolvedTheme, setPreference } = useTheme();
const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover({
  placement: 'right-end',
});

const options = [
  {
    value: 'light' as const,
    label: 'Light',
    description: 'Warm, bright surfaces.',
    icon: SunMedium,
  },
  {
    value: 'dark' as const,
    label: 'Dark',
    description: 'Dimmed surfaces for night use.',
    icon: MoonStar,
  },
  {
    value: 'system' as const,
    label: 'System',
    description: 'Follow your device theme.',
    icon: LaptopMinimal,
  },
];

const activeOption = computed(
  () => options.find((option) => option.value === preference.value) ?? options[2],
);
const activeIcon = computed(() => activeOption.value.icon);
const activeLabel = computed(() => {
  if (preference.value === 'system') {
    return `System · ${resolvedTheme.value === 'dark' ? 'Dark' : 'Light'}`;
  }
  return activeOption.value.label;
});
const buttonTitle = computed(() => `Theme: ${activeLabel.value}`);

const selectTheme = (value: ThemePreference): void => {
  setPreference(value);
  close();
};
</script>
