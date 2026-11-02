<template>
  <div class="relative w-full">
    <button
      ref="triggerRef"
      type="button"
      class="nav-link w-full"
      :class="compact ? 'justify-center px-0' : 'px-2'"
      :aria-label="`Account menu for ${username}`"
      :aria-controls="menuId"
      :aria-expanded="isOpen"
      :title="compact ? username : undefined"
      @click="toggle"
    >
      <span
        class="app-sidebar-avatar"
        aria-hidden="true"
      >{{ userInitial }}</span>
      <template v-if="!compact">
        <span class="min-w-0 flex-1 text-left">
          <span class="block truncate text-sm font-semibold">{{ username }}</span>
          <span
            v-if="role"
            class="app-sidebar-account-meta block text-xs font-normal"
          >{{ role }}</span>
        </span>
        <ChevronsUpDown class="h-4 w-4 shrink-0 opacity-60" />
      </template>
    </button>

    <Teleport to="body">
      <div
        v-if="isOpen"
        :id="menuId"
        ref="panelRef"
        class="theme-popover z-50 w-[16rem] p-2"
        :style="{ position: 'fixed', left: `${x}px`, top: `${y}px` }"
        data-testid="account-menu"
      >
        <p class="theme-section-muted truncate px-3 pb-2 pt-1 text-xs">
          Signed in as <span class="font-semibold">{{ username }}</span>
        </p>
        <button
          type="button"
          class="theme-mode-option items-center"
          @click="signOut"
        >
          <LogOut class="h-4 w-4 shrink-0" />
          <span class="text-sm font-semibold">Sign out</span>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ChevronsUpDown, LogOut } from 'lucide-vue-next';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';
import { useAuthStore } from '@/domain/session/store';

withDefaults(defineProps<{ compact?: boolean }>(), { compact: false });
const emit = defineEmits<{ signOut: [] }>();

const auth = useAuthStore();
const { isOpen, triggerRef, panelRef, x, y, toggle, close } = useFloatingPopover({
  placement: 'right-end',
});
const menuId = 'app-account-menu';

const username = computed(() => auth.user?.username || 'Signed in');
const userInitial = computed(() => username.value.charAt(0).toUpperCase());
const role = computed(() => {
  if (auth.user?.is_superuser) {
    return 'Superuser';
  }
  if (auth.canAccessStaffRoutes) {
    return 'Staff';
  }
  return null;
});

const signOut = (): void => {
  close();
  emit('signOut');
};
</script>
