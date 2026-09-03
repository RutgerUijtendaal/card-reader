<template>
  <div class="page-card space-y-6">
    <div class="theme-divider flex flex-wrap items-center justify-between gap-4 border-b pb-4">
      <div>
        <h3 class="theme-section-title text-base font-semibold">
          Card backs
        </h3>
        <p class="theme-section-muted mt-1 text-sm">
          Assign reusable artwork or manage the asset library.
        </p>
      </div>
      <div
        class="theme-tablist w-full sm:w-auto"
        aria-label="Card-back administration"
      >
        <button
          id="card-back-defaults-tab"
          type="button"
          class="theme-tab flex-1 sm:flex-none"
          :class="{ 'theme-tab-active': activeView === 'defaults' }"
          :aria-pressed="activeView === 'defaults'"
          @click="activeView = 'defaults'"
        >
          <SlidersHorizontal class="h-4 w-4" />
          Defaults
        </button>
        <button
          id="card-back-library-tab"
          type="button"
          class="theme-tab flex-1 sm:flex-none"
          :class="{ 'theme-tab-active': activeView === 'library' }"
          :aria-pressed="activeView === 'library'"
          @click="activeView = 'library'"
        >
          <Images class="h-4 w-4" />
          Library
          <span class="theme-pill theme-pill-neutral px-1.5 py-0.5 text-[11px]">
            {{ cardBacks.length }}
          </span>
        </button>
      </div>
    </div>

    <p
      v-if="errorMessage"
      class="theme-alert-danger"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <div
      v-if="activeView === 'defaults'"
      class="flex flex-col gap-8"
      role="region"
      aria-labelledby="card-back-defaults-tab"
    >
      <div class="theme-card-frame-muted rounded-xl px-4 py-3">
        <div class="flex flex-wrap items-center gap-2 text-sm">
          <span class="theme-section-muted mr-1 text-xs font-semibold uppercase tracking-wide">
            Resolution order
          </span>
          <span class="theme-pill theme-pill-neutral px-2 py-1">Individual card</span>
          <ArrowRight class="theme-section-muted h-4 w-4" />
          <span class="theme-pill theme-pill-neutral px-2 py-1">Role</span>
          <ArrowRight class="theme-section-muted h-4 w-4" />
          <span class="theme-pill theme-pill-neutral px-2 py-1">Evil faction</span>
          <ArrowRight class="theme-section-muted h-4 w-4" />
          <span class="theme-pill theme-pill-neutral px-2 py-1">Pool</span>
        </div>
        <p class="theme-section-muted mt-2 text-xs">
          Individual overrides are edited on the Card tab. Unset defaults continue to the next level.
        </p>
      </div>

      <section aria-labelledby="card-back-role-defaults-heading">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3
              id="card-back-role-defaults-heading"
              class="theme-section-title text-base font-semibold"
            >
              Role defaults
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              Global across every pool. Multi-role cards use the first configured role in canonical order.
            </p>
          </div>
          <span class="theme-section-muted text-xs">
            {{ configuredRoleCount }} of {{ CARD_ROLE_OPTIONS.length }} configured
          </span>
        </div>

        <div
          v-if="initialLoading"
          class="mt-3 space-y-3 animate-pulse"
          aria-label="Loading role defaults"
        >
          <div
            v-for="option in CARD_ROLE_OPTIONS"
            :key="option.value"
            class="grid gap-3 sm:grid-cols-[minmax(8rem,0.45fr)_minmax(14rem,1fr)_7rem]"
          >
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
          </div>
        </div>

        <div
          v-else
          class="theme-divider mt-3 border-t"
        >
          <CardBackDefaultRow
            v-for="option in CARD_ROLE_OPTIONS"
            :key="option.value"
            :model-value="roleDefaults[option.value]?.id ?? null"
            :label="option.label"
            :placeholder="`No ${option.label} role default`"
            :select-label="`${option.label} role default card back`"
            :assets="cardBacks"
            :disabled="defaultMutationLocked"
            @update:model-value="setRoleDefault(option.value, $event)"
          />
        </div>
      </section>

      <section aria-labelledby="card-back-faction-defaults-heading">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3
              id="card-back-faction-defaults-heading"
              class="theme-section-title text-base font-semibold"
            >
              Evil faction defaults
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              Evil cards only. Factions use canonical order, then fall back to the Evil pool default.
            </p>
          </div>
          <span class="theme-section-muted text-xs">
            {{ configuredFactionCount }} of {{ CARD_FACTION_OPTIONS.length }} configured
          </span>
        </div>

        <div
          v-if="initialLoading"
          class="mt-3 space-y-3 animate-pulse"
          aria-label="Loading Evil faction defaults"
        >
          <div
            v-for="option in CARD_FACTION_OPTIONS"
            :key="option.value"
            class="grid gap-3 sm:grid-cols-[minmax(8rem,0.45fr)_minmax(14rem,1fr)_7rem]"
          >
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
          </div>
        </div>

        <div
          v-else
          class="theme-divider mt-3 border-t"
        >
          <CardBackDefaultRow
            v-for="option in CARD_FACTION_OPTIONS"
            :key="option.value"
            :model-value="factionDefaults[option.value]?.id ?? null"
            :label="option.label"
            :placeholder="`No ${option.label} faction default`"
            :select-label="`${option.label} faction default card back`"
            :assets="cardBacks"
            :disabled="defaultMutationLocked"
            @update:model-value="setFactionDefault(option.value, $event)"
          />
        </div>
      </section>

      <section aria-labelledby="card-back-pool-defaults-heading">
        <div class="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3
              id="card-back-pool-defaults-heading"
              class="theme-section-title text-base font-semibold"
            >
              Pool defaults
            </h3>
            <p class="theme-section-muted mt-1 text-sm">
              The final fallback for cards in each pool.
            </p>
          </div>
          <span class="theme-section-muted text-xs">
            {{ configuredPoolCount }} of {{ CARD_POOL_OPTIONS.length }} configured
          </span>
        </div>

        <div
          v-if="initialLoading"
          class="mt-3 space-y-3 animate-pulse"
          aria-label="Loading pool defaults"
        >
          <div
            v-for="option in CARD_POOL_OPTIONS"
            :key="option.value"
            class="grid gap-3 sm:grid-cols-[minmax(8rem,0.45fr)_minmax(14rem,1fr)_7rem]"
          >
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
            <div class="h-10 rounded bg-[var(--color-surface-soft)]" />
          </div>
        </div>

        <div
          v-else
          class="theme-divider mt-3 border-t"
        >
          <CardBackDefaultRow
            v-for="option in CARD_POOL_OPTIONS"
            :key="option.value"
            :model-value="defaults[option.value]?.id ?? null"
            :label="option.label"
            :placeholder="`No ${option.label} pool default`"
            :select-label="`${option.label} default card back`"
            :assets="cardBacks"
            :disabled="defaultMutationLocked"
            @update:model-value="setDefault(option.value, $event)"
          />
        </div>
      </section>
    </div>

    <section
      v-else
      aria-labelledby="card-back-library-heading"
      role="region"
    >
      <div class="theme-divider flex flex-wrap items-end justify-between gap-4 border-b pb-4">
        <div>
          <h3
            id="card-back-library-heading"
            class="theme-section-title text-base font-semibold"
          >
            Card-back library
          </h3>
          <p
            class="theme-section-muted mt-1 text-sm"
            aria-live="polite"
          >
            {{ librarySummary }}
          </p>
        </div>
        <div class="flex w-full flex-wrap gap-2 sm:w-auto">
          <input
            v-model="searchQuery"
            class="input-base min-w-48 flex-1 sm:w-56 sm:flex-none"
            placeholder="Filter card backs"
            aria-label="Filter card backs"
          >
          <button
            class="btn-secondary inline-flex items-center gap-2"
            type="button"
            :disabled="loading"
            @click="loadCardBackData"
          >
            <RefreshCw
              class="h-4 w-4"
              :class="{ 'animate-spin': loading && hasLoaded }"
            />
            Refresh
          </button>
          <button
            class="btn-primary inline-flex items-center gap-2"
            type="button"
            @click="openUploadModal"
          >
            <Plus class="h-4 w-4" />
            Add card back
          </button>
        </div>
      </div>

      <div
        v-if="initialLoading"
        class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6"
        aria-label="Loading card-back library"
      >
        <div
          v-for="index in 6"
          :key="index"
          class="theme-card-frame-muted animate-pulse rounded-xl p-3"
        >
          <div class="aspect-[63/88] rounded-lg bg-[var(--color-surface-soft)]" />
          <div class="mt-3 h-4 w-2/3 rounded bg-[var(--color-surface-soft)]" />
          <div class="mt-2 h-3 w-1/2 rounded bg-[var(--color-surface-soft)]" />
        </div>
      </div>

      <div
        v-else-if="filteredCardBacks.length === 0"
        class="theme-empty-state mt-4 rounded-xl p-10 text-center text-sm"
      >
        <h4 class="theme-section-title font-semibold">
          {{ cardBacks.length === 0 ? 'No card backs yet' : 'No matching card backs' }}
        </h4>
        <p class="theme-section-muted mx-auto mt-1 max-w-md">
          {{ cardBacks.length === 0
            ? 'Add the first image to start the reusable card-back library.'
            : 'Try a different label.' }}
        </p>
        <button
          v-if="cardBacks.length === 0"
          class="btn-primary mt-4 inline-flex items-center gap-2"
          type="button"
          @click="openUploadModal"
        >
          <Plus class="h-4 w-4" />
          Add card back
        </button>
      </div>

      <div
        v-else
        class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6"
        role="list"
        aria-label="Card-back assets"
      >
        <article
          v-for="cardBack in filteredCardBacks"
          :key="cardBack.id"
          class="theme-card-frame rounded-xl p-3"
          role="listitem"
        >
          <div class="theme-card-image-well aspect-[63/88] overflow-hidden rounded-lg">
            <img
              v-if="cardBack.image_url"
              class="h-full w-full object-cover"
              :src="toAbsoluteApiUrl(cardBack.image_url)"
              :alt="cardBack.label"
              loading="lazy"
            >
            <div
              v-else
              class="theme-section-muted flex h-full flex-col items-center justify-center gap-2 p-4 text-center text-xs"
            >
              <ImageOff class="h-6 w-6" />
              Image unavailable
            </div>
          </div>

          <div class="mt-3 min-w-0">
            <div class="flex items-start justify-between gap-2">
              <h4 class="theme-section-title min-w-0 truncate text-sm font-semibold">
                {{ cardBack.label }}
              </h4>
              <span
                v-if="!cardBack.is_usable"
                class="theme-pill theme-pill-danger shrink-0 px-2 py-0.5 text-[11px]"
              >
                Missing
              </span>
            </div>
            <div class="mt-3 flex min-h-6 flex-wrap gap-1.5">
              <span
                v-for="pool in cardBack.default_for_pools"
                :key="pool"
                class="theme-pill theme-pill-success px-2 py-0.5 text-[11px]"
              >
                {{ poolLabel(pool) }} default
              </span>
              <span
                v-for="faction in cardBack.default_for_factions"
                :key="faction"
                class="theme-pill theme-pill-success px-2 py-0.5 text-[11px]"
              >
                {{ cardFactionLabel(faction) }} faction default
              </span>
              <span
                v-for="role in cardBack.default_for_roles"
                :key="role"
                class="theme-pill theme-pill-success px-2 py-0.5 text-[11px]"
              >
                {{ cardRoleLabel(role) }} role default
              </span>
              <span
                v-if="cardBack.default_for_pools.length === 0
                  && cardBack.default_for_roles.length === 0
                  && cardBack.default_for_factions.length === 0"
                class="theme-section-muted text-[11px]"
              >
                Not a default
              </span>
            </div>

            <div class="theme-divider theme-section-muted mt-3 border-t pt-3 text-[11px]">
              {{ cardBack.override_card_count }} card override{{ cardBack.override_card_count === 1 ? '' : 's' }}
            </div>
          </div>
        </article>
      </div>
    </section>

    <CardBackUploadModal
      :open="uploadModalOpen"
      :uploading="uploading"
      :error-message="uploadErrorMessage"
      @close="closeUploadModal"
      @submit="uploadSelectedCardBack"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ArrowRight, ImageOff, Images, Plus, RefreshCw, SlidersHorizontal } from 'lucide-vue-next';
import { toast } from 'vue-sonner';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { getApiErrorMessageWithCause as extractErrorMessage } from '@/shared/api/errors';
import {
  fetchCardBackDefaults,
  fetchCardBackFactionDefaults,
  fetchCardBackRoleDefaults,
  fetchCardBacks,
  setFactionCardBackDefault,
  setPoolCardBackDefault,
  setRoleCardBackDefault,
  uploadCardBack,
} from '@/domain/card-backs/api';
import type {
  CardBackDefaults,
  CardBackFactionDefaults,
  CardBackRecord,
  CardBackRoleDefaults,
} from '@/domain/card-backs/types';
import {
  CARD_FACTION_OPTIONS,
  cardFactionLabel,
  type CardFaction,
} from '@/domain/cards/cardFactions';
import { CARD_POOL_OPTIONS, type CardPool } from '@/domain/cards/cardPools';
import { CARD_ROLE_OPTIONS, cardRoleLabel, type CardRole } from '@/domain/cards/cardRoles';
import CardBackDefaultRow from '@/features/admin/components/CardBackDefaultRow.vue';
import CardBackUploadModal from '@/features/admin/components/CardBackUploadModal.vue';

const emptyDefaults = (): CardBackDefaults => ({ player: null, evil: null, neutral: null });
const emptyFactionDefaults = (): CardBackFactionDefaults => ({
  order: null,
  blood: null,
  dark: null,
  metal: null,
  fire: null,
});
const emptyRoleDefaults = (): CardBackRoleDefaults => ({
  hero: null,
  boss: null,
  location: null,
  boon: null,
  event: null,
  shop_item: null,
  directive: null,
  reminder: null,
  mana: null,
});
const cardBacks = ref<CardBackRecord[]>([]);
const defaults = ref<CardBackDefaults>(emptyDefaults());
const factionDefaults = ref<CardBackFactionDefaults>(emptyFactionDefaults());
const roleDefaults = ref<CardBackRoleDefaults>(emptyRoleDefaults());
const activeView = ref<'defaults' | 'library'>('defaults');
const loading = ref(false);
const hasLoaded = ref(false);
const uploading = ref(false);
const uploadModalOpen = ref(false);
const settingPool = ref<CardPool | null>(null);
const settingRole = ref<CardRole | null>(null);
const settingFaction = ref<CardFaction | null>(null);
const searchQuery = ref('');
const errorMessage = ref('');
const uploadErrorMessage = ref('');
let loadRequestVersion = 0;

const initialLoading = computed(() => loading.value && !hasLoaded.value);
const defaultMutationLocked = computed(() =>
  loading.value
  || settingPool.value !== null
  || settingRole.value !== null
  || settingFaction.value !== null,
);
const configuredPoolCount = computed(() =>
  Object.values(defaults.value).filter((value) => value !== null).length,
);
const configuredRoleCount = computed(() =>
  Object.values(roleDefaults.value).filter((value) => value !== null).length,
);
const configuredFactionCount = computed(() =>
  Object.values(factionDefaults.value).filter((value) => value !== null).length,
);
const filteredCardBacks = computed(() => {
  const query = searchQuery.value.trim().toLocaleLowerCase();
  if (!query) return cardBacks.value;
  return cardBacks.value.filter((asset) => asset.label.toLocaleLowerCase().includes(query));
});
const librarySummary = computed(() => {
  const total = cardBacks.value.length;
  const noun = total === 1 ? 'card back' : 'card backs';
  if (searchQuery.value.trim()) {
    return `${filteredCardBacks.value.length} of ${total} ${noun}`;
  }
  return `${total} ${noun}`;
});

const loadCardBackData = async (): Promise<void> => {
  const requestVersion = ++loadRequestVersion;
  loading.value = true;
  errorMessage.value = '';
  try {
    const [nextCardBacks, nextDefaults, nextRoleDefaults, nextFactionDefaults] = await Promise.all([
      fetchCardBacks(),
      fetchCardBackDefaults(),
      fetchCardBackRoleDefaults(),
      fetchCardBackFactionDefaults(),
    ]);
    if (requestVersion !== loadRequestVersion) return;
    cardBacks.value = nextCardBacks;
    defaults.value = nextDefaults;
    roleDefaults.value = nextRoleDefaults;
    factionDefaults.value = nextFactionDefaults;
  } catch (error) {
    if (requestVersion !== loadRequestVersion) return;
    errorMessage.value = extractErrorMessage(error, 'Card backs could not be loaded.');
  } finally {
    if (requestVersion === loadRequestVersion) {
      loading.value = false;
      hasLoaded.value = true;
    }
  }
};

const openUploadModal = (): void => {
  uploadErrorMessage.value = '';
  uploadModalOpen.value = true;
};

const closeUploadModal = (): void => {
  if (uploading.value) return;
  uploadModalOpen.value = false;
  uploadErrorMessage.value = '';
};

const uploadSelectedCardBack = async (payload: { file: File; label: string }): Promise<void> => {
  if (uploading.value) return;
  uploading.value = true;
  uploadErrorMessage.value = '';
  try {
    await uploadCardBack(payload.file, payload.label);
  } catch (error) {
    uploadErrorMessage.value = extractErrorMessage(error, 'Card back could not be uploaded.');
    toast.error(uploadErrorMessage.value);
    return;
  } finally {
    uploading.value = false;
  }
  uploadModalOpen.value = false;
  toast.success('Card-back asset uploaded.');
  await loadCardBackData();
};

const setDefault = async (cardPool: CardPool, cardBackId: string | null): Promise<void> => {
  if (
    settingPool.value !== null
    || settingRole.value !== null
    || settingFaction.value !== null
    || (defaults.value[cardPool]?.id ?? null) === cardBackId
  ) return;
  settingPool.value = cardPool;
  errorMessage.value = '';
  try {
    await setPoolCardBackDefault(cardPool, cardBackId);
    await loadCardBackData();
    toast.success(`${poolLabel(cardPool)} default updated.`);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Pool default could not be updated.');
    toast.error(errorMessage.value);
  } finally {
    settingPool.value = null;
  }
};

const setRoleDefault = async (
  role: CardRole,
  cardBackId: string | null,
): Promise<void> => {
  if (
    settingPool.value !== null
    || settingRole.value !== null
    || settingFaction.value !== null
    || (roleDefaults.value[role]?.id ?? null) === cardBackId
  ) return;
  settingRole.value = role;
  errorMessage.value = '';
  try {
    await setRoleCardBackDefault(role, cardBackId);
    await loadCardBackData();
    toast.success(`${cardRoleLabel(role)} role default updated.`);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Role default could not be updated.');
    toast.error(errorMessage.value);
  } finally {
    settingRole.value = null;
  }
};

const setFactionDefault = async (
  faction: CardFaction,
  cardBackId: string | null,
): Promise<void> => {
  if (
    settingPool.value !== null
    || settingRole.value !== null
    || settingFaction.value !== null
    || (factionDefaults.value[faction]?.id ?? null) === cardBackId
  ) return;
  settingFaction.value = faction;
  errorMessage.value = '';
  try {
    await setFactionCardBackDefault(faction, cardBackId);
    await loadCardBackData();
    toast.success(`${cardFactionLabel(faction)} faction default updated.`);
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, 'Faction default could not be updated.');
    toast.error(errorMessage.value);
  } finally {
    settingFaction.value = null;
  }
};

const poolLabel = (cardPool: CardPool): string =>
  CARD_POOL_OPTIONS.find((option) => option.value === cardPool)?.label ?? cardPool;

onMounted(() => { void loadCardBackData(); });
</script>
