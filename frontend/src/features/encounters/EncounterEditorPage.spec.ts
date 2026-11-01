/* eslint-disable vue/one-component-per-file */
import { createApp, defineComponent, h, nextTick, reactive, ref } from 'vue';
import { afterEach, expect, test, vi } from 'vitest';
import EncounterEditorPage from './EncounterEditorPage.vue';
import { emptyEncounter } from '@/domain/encounters/types';
import type { useEncounterEditor } from './composables/useEncounterEditor';
import type { useEncounterBrowser } from './composables/useEncounterBrowser';
let editor: ReturnType<typeof useEncounterEditor>;
let browser: ReturnType<typeof useEncounterBrowser>;
const createPublicationState = () => ({
  isCreating: ref(false),
  isReconciling: ref(false),
  isCreationUnknown: ref(false),
  hasTerminalNavigationRetry: ref(false),
  retry: vi.fn(),
});
let publicationState = createPublicationState();
vi.mock('./composables/useEncounterEditor', () => ({ useEncounterEditor: () => editor }));
vi.mock('./composables/useEncounterBrowser', () => ({ useEncounterBrowser: () => browser }));
vi.mock('@/shared/components/app/AppPageHeader.vue', () => ({
  default: defineComponent({
    setup:
      (_, { slots }) =>
      () =>
        h('header', [slots.center?.(), slots.actions?.(), slots.bottomLeft?.()]),
  }),
}));
vi.mock('@/shared/components/app/AppHeaderAction.vue', () => ({
  default: defineComponent({
    props: { label: { type: String, default: '' } },
    emits: ['click'],
    setup:
      (props, { emit }) =>
      () =>
        h('button', { onClick: () => emit('click') }, props.label),
  }),
}));
vi.mock('@/domain/cards/components/CardBuilderFilterBar.vue', () => ({
  default: { template: '<div data-testid="shared-filters" />' },
}));
vi.mock('@/domain/cards/components/CardBuilderGallery.vue', () => ({
  default: { template: '<div data-testid="shared-gallery" />' },
}));
vi.mock('./components/EncounterSummaryPanel.vue', () => ({
  default: { template: '<aside data-testid="encounter-deck" />' },
}));
vi.mock('./components/EncounterSelectionPanel.vue', () => ({
  default: { template: '<aside data-testid="boss-selection" />' },
}));
vi.mock('./components/EncounterDetailsForm.vue', () => ({
  default: { template: '<div data-testid="details" />' },
}));
vi.mock('@/shared/components/builders/BuilderDraftRecoveryModal.vue', () => ({
  default: { template: '<div />' },
}));
vi.mock('@/shared/components/builders/BuilderDraftConflictModal.vue', () => ({
  default: {
    props: { open: Boolean },
    template: '<div v-if="open" role="dialog" data-testid="draft-conflict" />',
  },
}));
const cleanups: Array<() => void> = [];
afterEach(() => cleanups.splice(0).forEach((fn) => fn()));
const mount = () => {
  publicationState = createPublicationState();
  editor = {
    id: 'saved',
    boards: { activeBoardEntries: ref([]) },
    form: reactive(emptyEncounter()),
    mode: ref('cards'),
    detailsOpen: ref(false),
    boss: ref(null),
    openDetails: vi.fn(),
    closeDetails: vi.fn(),
    setMode: vi.fn(),
    factions: ref([]),
    loading: ref(false),
    saving: ref(false),
    error: ref(''),
    locked: ref(false),
    readOnly: ref(false),
    dirty: ref(false),
    total: ref(0),
    issues: ref([]),
    autosync: ref(false),
    serverConflict: ref(false),
    minimum: ref(20),
    changeStatus: ref('Saved'),
    recoveryBusy: ref(false),
    draft: { pendingRecovery: ref(null), conflict: ref(null) },
    publication: publicationState,
    save: vi.fn(),
  } as unknown as ReturnType<typeof useEncounterEditor>;
  browser = {
    filters: { hoverMode: ref('tooltip') },
    gallery: { totalCount: ref(0) },
    error: ref(''),
  } as unknown as ReturnType<typeof useEncounterBrowser>;
  const target = document.createElement('div');
  document.body.appendChild(target);
  const app = createApp(EncounterEditorPage);
  app.mount(target);
  cleanups.push(() => {
    app.unmount();
    target.remove();
  });
  return target;
};
test('Cards uses the shared workbench: header filters, the pool, the Encounter panel, and a bottom status bar', () => {
  const target = mount();
  expect(target.querySelector('header [data-testid="shared-filters"]')).not.toBeNull();
  expect(target.querySelector('header nav[aria-label="Encounter editor sections"]')).toBeNull();
  const layout = target.querySelector('.builder-workspace-layout')!;
  expect(layout.children).toHaveLength(3);
  expect(layout.children[0].querySelector('[data-testid="shared-gallery"]')).not.toBeNull();
  expect(layout.children[1].getAttribute('data-testid')).toBe('encounter-deck');
  expect(layout.children[2].classList.contains('builder-workspace-footer')).toBe(true);
  expect(layout.children[2].querySelector('[aria-label="Encounter builder status"]')).not.toBeNull();
  const autosync = layout.querySelector('input[type="checkbox"]') as HTMLInputElement;
  autosync.checked = true;
  autosync.dispatchEvent(new Event('change', { bubbles: true }));
  expect(editor.autosync.value).toBe(true);
});
test('Boss keeps the same filters, gallery, and Encounter panel', async () => {
  const target = mount();
  editor.mode.value = 'boss';
  await nextTick();
  expect(target.querySelector('header [data-testid="shared-filters"]')).not.toBeNull();
  const layout = target.querySelector('.builder-workspace-layout')!;
  expect(layout.children[0].querySelector('[data-testid="shared-gallery"]')).not.toBeNull();
  expect(layout.children[1].getAttribute('data-testid')).toBe('encounter-deck');
});

test('Details opens as an overlay above the still-mounted pool and closes back to it', async () => {
  const target = mount();
  editor.detailsOpen.value = true;
  await nextTick();
  const overlay = target.querySelector('.builder-workspace-overlay');
  expect(overlay?.querySelector('[data-testid="details"]')).not.toBeNull();
  expect(target.querySelector('[data-testid="shared-gallery"]')).not.toBeNull();
  expect(target.querySelector('header [data-testid="shared-filters"]')).not.toBeNull();
  expect(target.querySelector('[aria-label="Encounter builder status"]')?.textContent).toContain('Saved');
  overlay?.querySelector<HTMLButtonElement>('button[aria-label="Close Encounter details"]')?.click();
  expect(editor.closeDetails).toHaveBeenCalledOnce();
});

test('an unresolved create keeps Retry accessible instead of covering it with a draft conflict', async () => {
  const target = mount();
  editor.draft.conflict.value = { kind: 'remote-deletion', slot: { kind: 'empty' } };
  publicationState.isCreationUnknown.value = true;
  await nextTick();
  expect(target.querySelector('[data-testid="draft-conflict"]')).toBeNull();
  const retry = [...target.querySelectorAll('button')].find(
    (button) => button.textContent?.trim() === 'Retry creation',
  )!;
  expect(retry.disabled).toBe(false);
  retry.click();
  expect(editor.publication.retry).toHaveBeenCalledOnce();
  publicationState.isCreationUnknown.value = false;
  publicationState.isCreating.value = true;
  await nextTick();
  expect(target.querySelector('[data-testid="draft-conflict"]')).toBeNull();
  publicationState.isCreating.value = false;
  publicationState.hasTerminalNavigationRetry.value = true;
  await nextTick();
  expect(target.querySelector('[data-testid="draft-conflict"]')).toBeNull();
  publicationState.hasTerminalNavigationRetry.value = false;
  await nextTick();
  expect(target.querySelector('[data-testid="draft-conflict"]')).not.toBeNull();
});
