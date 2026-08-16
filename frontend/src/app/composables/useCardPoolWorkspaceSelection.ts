import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { CardPool } from '@/domain/cards/cardPools';
import { useCardPoolWorkspaceStore } from '@/domain/cards/cardPoolWorkspace';
import { clearGalleryNavigationState } from '@/domain/cards/utils/gallery/galleryNavigation';
import { resolveWorkspaceSelectionDecision } from '@/app/router/workspaceCapabilities';

export const useCardPoolWorkspaceSelection = () => {
  const route = useRoute();
  const router = useRouter();
  const workspace = useCardPoolWorkspaceStore();
  const selectingPool = ref<CardPool | null>(null);
  let selectionAttempt = 0;
  let pendingPool: CardPool | null = null;
  let pendingSelection: Promise<boolean> | null = null;

  const executeSelection = async (cardPool: CardPool, attempt: number): Promise<boolean> => {
    const decision = resolveWorkspaceSelectionDecision(
      route,
      cardPool,
      workspace.activePool,
    );
    if (decision.kind === 'reject') {
      return false;
    }
    if (decision.kind === 'stay') {
      if (attempt !== selectionAttempt) {
        return false;
      }
      workspace.selectPool(cardPool);
      return true;
    }

    try {
      const navigationFailure = decision.navigation === 'replace'
        ? await router.replace(decision.location)
        : await router.push(decision.location);
      if (navigationFailure || attempt !== selectionAttempt) {
        return false;
      }
      if (
        decision.kind === 'replace-gallery'
        || decision.kind === 'update-resource-context'
        || decision.kind === 'fallback-gallery'
      ) {
        clearGalleryNavigationState();
      }
      workspace.selectPool(cardPool);
      return true;
    } catch {
      return false;
    }
  };

  const selectPool = (cardPool: CardPool): Promise<boolean> => {
    if (pendingSelection && pendingPool === cardPool) {
      return pendingSelection;
    }

    selectionAttempt += 1;
    const attempt = selectionAttempt;
    pendingPool = cardPool;
    selectingPool.value = cardPool;
    const previousSelection = pendingSelection;
    const selection = (previousSelection
      ? previousSelection.then(() => executeSelection(cardPool, attempt))
      : executeSelection(cardPool, attempt)
    ).finally(() => {
      if (attempt === selectionAttempt) {
        pendingPool = null;
        pendingSelection = null;
        selectingPool.value = null;
      }
    });
    pendingSelection = selection;
    return selection;
  };

  return {
    selectingPool,
    selectPool,
  };
};
