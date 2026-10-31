<template>
  <AppFormSection
    title="Visibility"
    :description="descriptions[modelValue]"
  >
    <div class="flex flex-wrap gap-2">
      <ChoicePill
        v-for="option in options"
        :key="option.value"
        :selected="modelValue === option.value"
        @click="$emit('update:modelValue', option.value)"
      >
        {{ option.label }}
      </ChoicePill>
    </div>
  </AppFormSection>
</template>
<script setup lang="ts">
import ChoicePill from '@/shared/components/ChoicePill.vue';
import AppFormSection from '@/shared/components/app/AppFormSection.vue';
type Visibility = 'private' | 'unlisted' | 'public';
defineProps<{ modelValue: Visibility; descriptions: Record<Visibility, string> }>();
defineEmits<{ 'update:modelValue': [value: Visibility] }>();
const options: Array<{ value: Visibility; label: string }> = [
  { value: 'private', label: 'Private' },
  { value: 'unlisted', label: 'Unlisted' },
  { value: 'public', label: 'Public' },
];
</script>
