import { onBeforeUnmount, onMounted } from 'vue';
import { toast, useVueSonner } from 'vue-sonner';

const defaultToastPosition = 'bottom-right';

export function useToastDismissOnClick(): void {
  const { activeToasts } = useVueSonner();

  const dismissToastFromClick = (event: MouseEvent): void => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    if (target.closest('[data-button], [data-close-button], a, button, input, select, textarea, label')) {
      return;
    }

    const toastElement = target.closest('[data-sonner-toast]');
    if (!(toastElement instanceof HTMLElement)) {
      return;
    }

    const indexValue = toastElement.dataset.index;
    const yPosition = toastElement.dataset.yPosition;
    const xPosition = toastElement.dataset.xPosition;
    if (!indexValue || !yPosition || !xPosition) {
      return;
    }

    const index = Number(indexValue);
    if (!Number.isInteger(index) || index < 0) {
      return;
    }

    const position = `${yPosition}-${xPosition}`;
    const matchingToast = activeToasts.value
      .filter((entry) => (entry.position ?? defaultToastPosition) === position)
      [index];
    if (!matchingToast) {
      return;
    }

    toast.dismiss(matchingToast.id);
  };

  onMounted(() => {
    document.addEventListener('click', dismissToastFromClick);
  });

  onBeforeUnmount(() => {
    document.removeEventListener('click', dismissToastFromClick);
  });
}
