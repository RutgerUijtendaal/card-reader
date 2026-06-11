import { onKeyStroke } from '@vueuse/core';
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, toAbsoluteApiUrl } from '@/api/client';
import { useAuthStore } from '@/modules/auth/authStore';
import {
  buildCardEditorReturnLocation,
  buildCardReturnLocation,
  getCardReturnLabel,
} from '@/composables/cards/cardReturnState';
import { useGalleryCardNavigation } from '@/composables/card-gallery/galleryNavigation';
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
  const isLoadingInitial = ref(false);
  let loadRequestId = 0;

  const selectedVersion = computed<CardVersionDetail | null>(
    () => versions.value.find((version) => version.version_id === selectedVersionId.value) ?? null,
  );

  const canEdit = computed(() => auth.canAccessStaffRoutes && selectedVersion.value?.editable);
  const backButtonLabel = computed(() => `Back to ${getCardReturnLabel(route.query)}`);

  const loadCard = async (): Promise<void> => {
    const requestId = ++loadRequestId;
    const cardId = String(route.params.id);
    isLoadingInitial.value = true;
    try {
      const [cardResponse, versionsResponse, filtersResponse] = await Promise.all([
        api.get<CardDetail>(`/cards/${cardId}`),
        api.get<CardVersionDetail[]>(`/cards/${cardId}/generations`),
        api.get<CardFiltersResponse>('/cards/filters'),
      ]);

      if (requestId !== loadRequestId) {
        return;
      }

      card.value = cardResponse.data;
      versions.value = versionsResponse.data;
      symbolByKey.value = Object.fromEntries(
        (filtersResponse.data.symbols ?? []).map((row) => [row.key, row]),
      );
      selectedVersionId.value =
        versions.value.find((version) => version.is_latest)?.version_id ??
        versions.value[0]?.version_id ??
        '';
    } finally {
      if (requestId === loadRequestId) {
        isLoadingInitial.value = false;
      }
    }
  };

  const goBack = (): void => {
    void router.push(buildCardReturnLocation(route.query));
  };

  const openEditor = (): void => {
    void router.push(buildCardEditorReturnLocation(String(route.params.id), route.query));
  };

  const selectVersion = (versionId: string): void => {
    selectedVersionId.value = versionId;
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
    isLoadingInitial,
    canEdit,
    backButtonLabel,
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
