import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test, vi } from 'vitest';
import ImportSourcePicker from '@/features/import-jobs/components/ImportSourcePicker.vue';

const mountPicker = () => {
  const selectedFiles = ref<File[]>([]);
  const resetKey = ref(0);
  const onSelect = vi.fn((files: File[]) => {
    selectedFiles.value = files;
  });
  const onClear = vi.fn(() => {
    selectedFiles.value = [];
    resetKey.value += 1;
  });
  const host = document.createElement('div');
  document.body.appendChild(host);
  const app = createApp(
    defineComponent({
      setup() {
        return () => h(ImportSourcePicker, {
          files: selectedFiles.value,
          resetKey: resetKey.value,
          onSelect,
          onClear,
        });
      },
    }),
  );
  app.mount(host);
  return { app, host, selectedFiles, resetKey, onSelect, onClear };
};

describe('ImportSourcePicker', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('opens image and folder inputs through styled buttons', () => {
    const mounted = mountPicker();
    const inputs = mounted.host.querySelectorAll<HTMLInputElement>('input[type="file"]');
    const imageClick = vi.spyOn(inputs[0], 'click');
    const folderClick = vi.spyOn(inputs[1], 'click');

    Array.from(mounted.host.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('Choose image'))
      ?.click();
    Array.from(mounted.host.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('Choose folder'))
      ?.click();

    expect(imageClick).toHaveBeenCalledOnce();
    expect(folderClick).toHaveBeenCalledOnce();
    expect(inputs[1].hasAttribute('webkitdirectory')).toBe(true);

    mounted.app.unmount();
  });

  test('selects supported files and shows a bounded summary that can be cleared', async () => {
    const mounted = mountPicker();
    const files = Array.from(
      { length: 6 },
      (_, index) => new File(['image'], `card-${index + 1}.png`, { type: 'image/png' }),
    );
    const directoryInput = mounted.host.querySelectorAll<HTMLInputElement>('input[type="file"]')[1];
    Object.defineProperty(directoryInput, 'files', { configurable: true, value: files });
    directoryInput.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();

    expect(mounted.onSelect).toHaveBeenCalledWith(files);
    expect(mounted.host.textContent).toContain('Selected folder');
    expect(mounted.host.textContent).toContain('6 images');
    expect(mounted.host.textContent).toContain('+1 more image');
    expect(mounted.host.textContent).not.toContain('card-6.png');

    Array.from(mounted.host.querySelectorAll('button'))
      .find((button) => button.textContent?.trim() === 'Clear')
      ?.click();
    await nextTick();

    expect(mounted.onClear).toHaveBeenCalledOnce();
    expect(mounted.host.textContent).not.toContain('Selected folder');

    mounted.app.unmount();
  });

  test('accepts image drops while reporting unsupported files', async () => {
    const mounted = mountPicker();
    const image = new File(['image'], 'card.webp', { type: 'image/webp' });
    const textFile = new File(['notes'], 'notes.txt', { type: 'text/plain' });
    const dropTarget = mounted.host.querySelector('.border-dashed');
    const dropEvent = new Event('drop', { bubbles: true, cancelable: true });
    Object.defineProperty(dropEvent, 'dataTransfer', {
      configurable: true,
      value: { files: [image, textFile] },
    });
    dropTarget?.dispatchEvent(dropEvent);
    await nextTick();

    expect(mounted.onSelect).toHaveBeenCalledWith([image]);
    expect(mounted.host.textContent).toContain('1 unsupported file was ignored.');
    expect(mounted.host.textContent).toContain('Dropped images');

    mounted.selectedFiles.value = [];
    mounted.resetKey.value += 1;
    await nextTick();
    expect(mounted.host.textContent).not.toContain('unsupported file');

    mounted.app.unmount();
  });

  test('clears a previous selection when its replacement has no supported images', async () => {
    const mounted = mountPicker();
    const previousImage = new File(['image'], 'previous.png', { type: 'image/png' });
    mounted.selectedFiles.value = [previousImage];
    await nextTick();

    const unsupportedFile = new File(['notes'], 'notes.txt', { type: 'text/plain' });
    const directoryInput = mounted.host.querySelectorAll<HTMLInputElement>('input[type="file"]')[1];
    Object.defineProperty(directoryInput, 'files', {
      configurable: true,
      value: [unsupportedFile],
    });
    directoryInput.dispatchEvent(new Event('change', { bubbles: true }));
    await nextTick();

    expect(mounted.onClear).toHaveBeenCalledOnce();
    expect(mounted.selectedFiles.value).toEqual([]);
    expect(mounted.host.textContent).not.toContain('previous.png');
    expect(mounted.host.textContent).toContain('Choose PNG, JPG, JPEG, or WebP card images.');
    expect(mounted.host.querySelectorAll<HTMLInputElement>('input[type="file"]')[1].files)
      .toHaveLength(0);

    mounted.app.unmount();
  });
});
