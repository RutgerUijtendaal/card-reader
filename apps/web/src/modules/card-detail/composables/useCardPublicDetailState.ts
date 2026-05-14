import { onKeyStroke } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, DEFAULT_API_BASE_URL } from '@/api/client';
import { useAuthStore } from '@/modules/auth/authStore';
import { useGalleryCardNavigation } from '@/modules/card-search/galleryNavigation';
import type {
  CardDetail,
  CardFiltersResponse,
  CardVersionDetail,
  SymbolLookupMap,
} from '@/modules/card-detail/types';
import { isEditableKeyboardTarget } from '@/utils/keyboard';

export const useCardPublicDetailState = () => {
  const route = useRoute();
  const router = useRouter();
  const auth = useAuthStore();

  const card = ref<CardDetail | null>(null);
  const versions = ref<CardVersionDetail[]>([]);
  const selectedVersionId = ref<string>('');
  const symbolByKey = ref<SymbolLookupMap>({});
  const galleryNavigation = useGalleryCardNavigation(route, router, 'detail');

  const selectedVersion = computed<CardVersionDetail | null>(
    () => versions.value.find((version) => version.version_id === selectedVersionId.value) ?? null,
  );

  const canEdit = computed(() => auth.canAccessStaffRoutes && selectedVersion.value?.editable);

  const loadCard = async (): Promise<void> => {
    const cardId = String(route.params.id);
    const [cardResponse, versionsResponse, filtersResponse] = await Promise.all([
      api.get<CardDetail>(`/cards/${cardId}`),
      api.get<CardVersionDetail[]>(`/cards/${cardId}/generations`),
      api.get<CardFiltersResponse>('/cards/filters'),
    ]);

    card.value = cardResponse.data;
    versions.value = versionsResponse.data;
    symbolByKey.value = Object.fromEntries(
      (filtersResponse.data.symbols ?? []).map((row) => [row.key, row]),
    );
    selectedVersionId.value =
      versions.value.find((version) => version.is_latest)?.version_id ??
      versions.value[0]?.version_id ??
      '';
  };

  const goBack = (): void => {
    void router.push('/cards');
  };

  const openEditor = (): void => {
    void router.push(`/cards/${route.params.id}/edit`);
  };

  const selectVersion = (versionId: string): void => {
    selectedVersionId.value = versionId;
  };

  const toAbsoluteApiUrl = (urlPath: string): string => {
    const base = api.defaults.baseURL ?? DEFAULT_API_BASE_URL;
    if (urlPath.startsWith('http://') || urlPath.startsWith('https://')) {
      return urlPath;
    }
    return `${base.replace(/\/$/, '')}/${urlPath.replace(/^\//, '')}`;
  };

  const formatDate = (value: string): string => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleDateString();
  };

  onKeyStroke(['ArrowLeft', 'ArrowRight'], (event) => {
    if (!galleryNavigation.hasGalleryContext.value || isEditableKeyboardTarget(event)) {
      return;
    }

    if (event.key === 'ArrowLeft' && galleryNavigation.previousCardId.value) {
      event.preventDefault();
      galleryNavigation.goToPreviousCard();
      return;
    }

    if (event.key === 'ArrowRight' && (galleryNavigation.nextCardId.value || galleryNavigation.hasMoreResults.value)) {
      event.preventDefault();
      void galleryNavigation.goToNextCard();
    }
  });

  watch(() => route.params.id, loadCard);

  return {
    card,
    versions,
    selectedVersionId,
    selectedVersion,
    symbolByKey,
    canEdit,
    hasGalleryContext: galleryNavigation.hasGalleryContext,
    previousCardId: galleryNavigation.previousCardId,
    nextCardId: galleryNavigation.nextCardId,
    hasMoreResults: galleryNavigation.hasMoreResults,
    isLoadingMoreCards: galleryNavigation.isLoadingMoreCards,
    positionLabel: galleryNavigation.positionLabel,
    loadCard,
    goBack,
    openEditor,
    selectVersion,
    goToPreviousCard: galleryNavigation.goToPreviousCard,
    goToNextCard: () => {
      void galleryNavigation.goToNextCard();
    },
    toAbsoluteApiUrl,
    formatDate,
  };
};
