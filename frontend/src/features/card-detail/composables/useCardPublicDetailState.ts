import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { toAbsoluteApiUrl } from '@/shared/api/client';
import { fetchCard, fetchCardFilters, fetchCardVersions } from '@/domain/cards/api';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import { useAuthStore } from '@/domain/session/store';
import {
  buildCardEditorReturnLocation,
  buildCardReturnLocation,
  getCardReturnLabel,
} from '@/domain/card-navigation/cardReturnState';
import { useGalleryCardNavigation } from '@/domain/cards/utils/gallery/galleryNavigation';
import type { CardVersionDetail, SymbolLookupMap } from '@/domain/cards/types';
import type { CardDetail } from '@/features/card-detail/types';
import { formatCardDetailDate } from '@/features/card-detail/utils/cardDetailFormatters';

export const resolvePublicCardVersionId = (
  availableVersions: ReadonlyArray<Pick<CardVersionDetail, 'version_id' | 'is_latest'>>,
  requestedVersionId: unknown,
): string => {
  const requestedId = typeof requestedVersionId === 'string' ? requestedVersionId : '';
  return availableVersions.find((version) => version.version_id === requestedId)?.version_id
    ?? availableVersions.find((version) => version.is_latest)?.version_id
    ?? availableVersions[0]?.version_id
    ?? '';
};

export const useCardPublicDetailState = () => {
  const route = useRoute();
  const router = useRouter();
  const auth = useAuthStore();
  const workspace = useCardPoolWorkspaceStore();

  const card = ref<CardDetail | null>(null);
  const versions = ref<CardVersionDetail[]>([]);
  const selectedVersionId = ref<string>('');
  const symbolByKey = ref<SymbolLookupMap>({});
  const galleryNavigation = useGalleryCardNavigation(route, router, 'detail');
  const isLoadingInitial = ref(true);
  let loadRequestId = 0;

  const selectedVersion = computed<CardVersionDetail | null>(
    () => versions.value.find((version) => version.version_id === selectedVersionId.value) ?? null,
  );

  const canEdit = computed(() => auth.canAccessStaffRoutes && selectedVersion.value?.editable);
  const backButtonLabel = computed(() => `Back to ${getCardReturnLabel(route.query)}`);

  const loadCard = async (): Promise<void> => {
    const requestId = ++loadRequestId;
    const workspaceGeneration = workspace.generation;
    const cardId = String(route.params.id);
    isLoadingInitial.value = true;
    card.value = null;
    versions.value = [];
    selectedVersionId.value = '';
    symbolByKey.value = {};
    try {
      const [cardResponse, versionsResponse, filtersResponse] = await Promise.all([
        fetchCard<CardDetail>(cardId),
        fetchCardVersions(cardId),
        fetchCardFilters(),
      ]);

      if (requestId !== loadRequestId || workspaceGeneration !== workspace.generation) {
        return;
      }

      card.value = cardResponse;
      versions.value = versionsResponse;
      symbolByKey.value = Object.fromEntries(
        (filtersResponse.symbols ?? []).map((row) => [row.key, row]),
      );
      selectedVersionId.value = resolvePublicCardVersionId(versions.value, route.query.version_id);
    } finally {
      if (requestId === loadRequestId && workspaceGeneration === workspace.generation) {
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
    if (route.query.version_id !== versionId) {
      void router.replace({
        query: {
          ...route.query,
          version_id: versionId,
        },
      });
    }
  };

  watch(() => route.params.id, loadCard);
  watch(() => workspace.generation, loadCard, { flush: 'sync' });
  watch(
    () => route.query.version_id,
    (versionId) => {
      selectedVersionId.value = resolvePublicCardVersionId(versions.value, versionId);
    },
  );

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
    formatDate: formatCardDetailDate,
  };
};
