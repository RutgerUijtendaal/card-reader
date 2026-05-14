<template>
  <div class="group w-full">
    <div class="relative transition duration-200 hover:-translate-y-1">
      <RouterLink
        :to="buildDetailLocation(card.id, 'detail')"
        class="block"
      >
        <img
          v-if="card.image_url"
          :src="toAbsoluteApiUrl(card.image_url)"
          alt="Card image"
          class="block h-[27rem] w-full object-contain transition duration-300 group-hover:scale-[1.02]"
          loading="lazy"
          decoding="async"
        >
        <div
          v-else
          class="flex h-[27rem] items-center justify-center rounded-xl border border-dashed border-slate-300 text-sm text-slate-500"
        >
          No image
        </div>
      </RouterLink>

      <div
        v-if="auth.canAccessStaffRoutes"
        class="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center p-3 opacity-0 transition duration-200 group-hover:opacity-100"
      >
        <RouterLink
          :to="buildDetailLocation(card.id, 'edit')"
          class="pointer-events-auto inline-flex items-center gap-1.5 rounded-full border border-slate-900/10 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-xl transition hover:bg-slate-50"
        >
          <Pencil class="h-3.5 w-3.5" />
          <span>Edit</span>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';
import { api, DEFAULT_API_BASE_URL } from '@/api/client';
import { Pencil } from 'lucide-vue-next';
import { useAuthStore } from '@/modules/auth/authStore';
import { buildCardDetailLocation } from '@/modules/card-search/galleryNavigation';
import type {
  CardHoverTooltipModel,
} from '@/components/cards/cardModels';

export type CardGalleryItemModel = CardHoverTooltipModel & {
  image_url: string | null;
};

defineProps<{
  card: CardGalleryItemModel;
}>();

const auth = useAuthStore();
const route = useRoute();

const buildDetailLocation = (cardId: string, mode: 'detail' | 'edit') =>
  buildCardDetailLocation(cardId, route.query, mode);

const toAbsoluteApiUrl = (urlPath: string): string => {
  const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
  if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
    return urlPath;
  }
  return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
};
</script>
