<template>
  <div
    class="relative w-full"
    :class="compact ? 'flex justify-center' : ''"
  >
    <button
      v-if="showsHotkeysPopover"
      ref="triggerRef"
      type="button"
      :class="compact ? 'theme-hotkeys-button-compact' : 'theme-hotkeys-panel theme-hotkeys-panel-button'"
      :aria-label="popoverButtonLabel"
      :aria-controls="popoverId"
      :aria-expanded="isOpen"
      :title="compact ? popoverButtonLabel : undefined"
      @click="toggle"
    >
      <template v-if="compact">
        <span class="theme-hotkeys-icon-wrap-compact">
          <Keyboard class="h-4 w-4" />
        </span>
      </template>

      <template v-else>
        <span class="flex w-full items-center gap-2">
          <span class="theme-hotkeys-icon-wrap">
            <Keyboard class="h-4 w-4" />
          </span>
          <span class="min-w-0 flex-1 text-left">
            <span class="block text-sm font-semibold">Hotkeys</span>
            <span class="block text-xs opacity-75">Playtester essentials</span>
          </span>
          <ChevronRight
            class="h-4 w-4 shrink-0 transition"
            :class="isOpen ? 'rotate-180' : ''"
          />
        </span>

        <span
          class="grid w-full gap-2 text-sm"
          data-testid="playtester-hotkey-essentials"
        >
          <span
            v-for="hotkey in playtesterEssentials"
            :key="hotkey.id"
            class="flex items-center justify-between gap-3"
          >
            <span class="opacity-80">{{ hotkey.label }}</span>
            <span class="inline-flex shrink-0 items-center gap-1">
              <span
                v-for="key in hotkey.keys"
                :key="key"
                class="theme-hotkey-chip"
              >
                {{ key }}
              </span>
            </span>
          </span>

          <span class="theme-hotkeys-more-link flex min-h-5 w-full items-center justify-between gap-3">
            <span>View all shortcuts</span>
            <span class="text-xs font-semibold">{{ playtesterHotkeyCount }}</span>
          </span>
        </span>
      </template>
    </button>

    <div
      v-else
      class="theme-hotkeys-panel"
      :data-hotkey-count="globalHotkeys.length"
    >
      <div class="flex items-center gap-2">
        <span class="theme-hotkeys-icon-wrap">
          <Keyboard class="h-4 w-4" />
        </span>
        <div class="min-w-0">
          <p class="text-sm font-semibold">
            Hotkeys
          </p>
          <p class="text-xs opacity-75">
            Search and quick actions
          </p>
        </div>
      </div>

      <div class="space-y-2 text-sm">
        <div
          v-for="hotkey in globalHotkeys"
          :key="hotkey.id"
          class="flex items-center justify-between gap-3"
        >
          <span class="opacity-80">{{ hotkey.label }}</span>
          <span class="inline-flex shrink-0 items-center gap-1">
            <span
              v-for="key in hotkey.keys"
              :key="key"
              class="theme-hotkey-chip"
            >
              {{ key }}
            </span>
          </span>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="isOpen"
        :id="popoverId"
        ref="panelRef"
        class="theme-popover app-scrollbar z-50 w-[22rem] max-w-[calc(100vw-1rem)] overflow-y-auto p-3"
        :style="popoverStyle"
        role="region"
        :aria-labelledby="popoverTitleId"
        data-testid="hotkeys-popover"
      >
        <div class="flex items-center gap-3 px-1 pb-3">
          <span class="theme-hotkeys-icon-wrap">
            <Keyboard class="h-4 w-4" />
          </span>
          <div class="min-w-0">
            <p
              :id="popoverTitleId"
              class="text-sm font-semibold"
            >
              {{ popoverTitle }}
            </p>
            <p class="text-xs opacity-70">
              {{ popoverDescription }}
            </p>
          </div>
        </div>

        <section
          v-for="group in activeHotkeyGroups"
          :key="group.id"
          class="theme-divider border-t py-3"
        >
          <h3 class="px-1 text-[11px] font-semibold uppercase tracking-[0.16em] opacity-65">
            {{ group.label }}
          </h3>
          <div class="mt-2 space-y-2">
            <div
              v-for="hotkey in group.hotkeys"
              :key="hotkey.id"
              class="flex items-center justify-between gap-4 rounded-lg px-1 py-1 text-sm"
            >
              <span class="opacity-80">{{ hotkey.label }}</span>
              <span class="inline-flex shrink-0 items-center gap-1">
                <span
                  v-for="key in hotkey.keys"
                  :key="key"
                  class="theme-hotkey-chip"
                >
                  {{ key }}
                </span>
              </span>
            </div>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, type CSSProperties } from 'vue';
import { ChevronRight, Keyboard } from 'lucide-vue-next';
import { useRoute } from 'vue-router';
import { useFloatingPopover } from '@/shared/composables/useFloatingPopover';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import { useAuthStore } from '@/domain/session/store';

type HotkeyDefinition = {
  id: string;
  label: string;
  keys: string[];
};

type HotkeyGroup = {
  id: string;
  label: string;
  hotkeys: HotkeyDefinition[];
};

const props = withDefaults(
  defineProps<{
    compact?: boolean;
  }>(),
  {
    compact: false,
  },
);

const auth = useAuthStore();
const workspace = useCardPoolWorkspaceStore();
const route = useRoute();
const { isOpen, triggerRef, panelRef, x, y, availableHeight, toggle, close } = useFloatingPopover({
  placement: 'right-end',
  fitAvailableHeight: true,
});

const playtesterHotkeyGroups: HotkeyGroup[] = [
  {
    id: 'turn',
    label: 'Turn',
    hotkeys: [
      { id: 'next-turn', label: 'Next turn', keys: ['N'] },
      { id: 'untap-all', label: 'Untap all', keys: ['U'] },
      { id: 'draw', label: 'Draw', keys: ['D'] },
    ],
  },
  {
    id: 'cards-board',
    label: 'Cards & board',
    hotkeys: [
      { id: 'tap', label: 'Tap', keys: ['T'] },
      { id: 'flip', label: 'Flip', keys: ['F'] },
      { id: 'group', label: 'Group', keys: ['G'] },
      { id: 'delete', label: 'Delete', keys: ['Del'] },
      { id: 'copy-paste', label: 'Copy/Paste', keys: ['Ctrl+C', 'Ctrl+V'] },
    ],
  },
  {
    id: 'stacks',
    label: 'Stacks',
    hotkeys: [
      { id: 'library', label: 'Library', keys: ['O'] },
      { id: 'shuffle', label: 'Shuffle', keys: ['R'] },
    ],
  },
  {
    id: 'history',
    label: 'History',
    hotkeys: [
      { id: 'undo', label: 'Undo', keys: ['Ctrl+Z'] },
      { id: 'redo', label: 'Redo', keys: ['Ctrl+Shift+Z', 'Ctrl+Y'] },
    ],
  },
  {
    id: 'view',
    label: 'View',
    hotkeys: [
      { id: 'zoom-card', label: 'Zoom card', keys: ['Middle Mouse'] },
      { id: 'scale', label: 'Scale', keys: ['Alt+Wheel'] },
    ],
  },
];

const isPlaytesterRoute = computed(() => route.path === '/playtester' || route.path.startsWith('/playtester/'));
const showsHotkeysPopover = computed(() => props.compact || isPlaytesterRoute.value);
const playtesterEssentials = playtesterHotkeyGroups[0].hotkeys;
const playtesterHotkeyCount = playtesterHotkeyGroups.reduce((total, group) => total + group.hotkeys.length, 0);
const globalHotkeys = computed<HotkeyDefinition[]>(() => [
  { id: 'search', label: 'Search', keys: ['/'] },
  { id: 'hover-mode', label: 'Hover Mode', keys: ['Alt+1/2/3/4/5'] },
  { id: 'hover-size', label: 'Hover Size', keys: ['Alt+Wheel'] },
  ...(auth.authenticated && workspace.activePool === 'player'
    ? [{ id: 'new-deck', label: 'New Deck', keys: ['N', 'N'] }]
    : []),
]);
const activeHotkeyGroups = computed<HotkeyGroup[]>(() => isPlaytesterRoute.value
  ? playtesterHotkeyGroups
  : [{ id: 'global', label: 'Global', hotkeys: globalHotkeys.value }]);
const popoverTitle = computed(() => isPlaytesterRoute.value ? 'Playtester hotkeys' : 'Global hotkeys');
const popoverDescription = computed(() => isPlaytesterRoute.value
  ? 'Commands available across the playtest surface.'
  : 'Search and navigation commands.');
const popoverButtonLabel = computed(() => isPlaytesterRoute.value
  ? 'Open all playtester hotkeys'
  : 'Open global hotkeys');
const popoverId = 'app-hotkeys-popover';
const popoverTitleId = 'app-hotkeys-popover-title';
const popoverStyle = computed<CSSProperties>(() => ({
  position: 'fixed',
  left: `${x.value}px`,
  top: `${y.value}px`,
  maxHeight: availableHeight.value === null
    ? 'calc(100vh - 1rem)'
    : `${availableHeight.value}px`,
}));

watch(() => route.path, close);
watch(() => props.compact, close);
watch(() => workspace.activePool, close);
</script>
