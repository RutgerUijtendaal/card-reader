import { createApp, nextTick, h } from 'vue';
import { createMemoryHistory, createRouter, RouterView } from 'vue-router';
import { createPinia } from 'pinia';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import CardBackImportPage from '@/features/admin/CardBackImportPage.vue';

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock('@/shared/api/client', () => ({
  api: { get, post },
  toAbsoluteApiUrl: (url: string) => url,
}));
const hero = {
  id: 'hero', name: 'Silver Knight', card_pool: 'player', card_roles: ['hero'],
  card_factions: [], lifecycle_status: 'active', card_back_override_id: 'old',
  effective_card_back: { source: 'override', asset: { label: 'Previous artwork', image_url: null } },
};
const cleanups: (() => void)[] = [];
beforeEach(() => {
  vi.resetAllMocks();
  URL.createObjectURL = vi.fn(() => 'blob:preview');
  URL.revokeObjectURL = vi.fn();
  get.mockImplementation((url: string) => Promise.resolve({
    data: url === '/cards' ? { results: [hero], next_page: null } : hero,
  }));
});
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup());
  document.body.innerHTML = '';
});
const mount = async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/admin/card-backs/import', component: CardBackImportPage },
      { path: '/admin', component: { template: '<p>Library</p>' } },
    ],
  });
  const container = document.createElement('div');
  document.body.append(container);
  const app = createApp({ render: () => h(RouterView) });
  app.use(createPinia());
  app.use(router);
  await router.push('/admin/card-backs/import');
  await router.isReady();
  app.mount(container);
  cleanups.push(() => app.unmount());
  await vi.waitFor(() => expect(container.textContent).toContain('Choose images to start'));
  const input = container.querySelector<HTMLInputElement>('input[type="file"]')!;
  Object.defineProperty(input, 'files', { value: [new File(['image'], 'Silver_Knight.png')], configurable: true });
  input.dispatchEvent(new Event('change'));
  await nextTick();
  return { container, router };
};
const button = (label: string): HTMLButtonElement => {
  const found = Array.from(document.body.querySelectorAll('button')).find((item) => item.textContent?.includes(label));
  if (!found) throw new Error(`Missing button: ${label}`);
  return found;
};

test('shows a suggestion without assigning it, then requires explicit override confirmation', async () => {
  const { container } = await mount();
  expect(container.textContent).toContain('Suggested: Silver Knight');
  expect(container.textContent).toContain('Library only — no hero assignment');
  expect(get).not.toHaveBeenCalledWith('/cards/hero');
  button('Use this hero').click();
  await vi.waitFor(() => expect(container.textContent).toContain('Previous artwork'));
  expect(button('Import prepared rows').disabled).toBe(true);
  const checkbox = container.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
  checkbox.checked = true;
  checkbox.dispatchEvent(new Event('change'));
  await nextTick();
  expect(button('Import prepared rows').disabled).toBe(false);
  post.mockResolvedValue({ data: { outcome: 'succeeded', asset: { id: 'new' }, hero_card_id: 'hero' } });
  button('Import prepared rows').click();
  await vi.waitFor(() => expect(container.textContent).toContain('Imported and assigned to hero'));
  const payload = post.mock.calls[0]?.[1] as FormData;
  expect(payload.get('hero_card_id')).toBe('hero');
  expect(payload.get('expected_override_id')).toBe('old');
});

test('asks before leaving an unsubmitted draft and supports cancel and discard', async () => {
  const { router } = await mount();
  const navigation = router.push('/admin');
  await vi.waitFor(() => expect(document.body.textContent).toContain('Discard this import draft?'));
  button('Cancel').click();
  await navigation;
  expect(router.currentRoute.value.path).toBe('/admin/card-backs/import');
  const unload = new Event('beforeunload', { cancelable: true });
  expect(window.dispatchEvent(unload)).toBe(false);
  const leaving = router.push('/admin');
  await vi.waitFor(() => expect(document.body.textContent).toContain('Discard this import draft?'));
  button('Discard draft').click();
  await leaving;
  expect(router.currentRoute.value.path).toBe('/admin');
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview');
});

test('blocks navigation during unresolved requests and releases it after reconciliation', async () => {
  const { router, container } = await mount();
  post.mockRejectedValue(new Error('lost response'));
  get.mockRejectedValue(new Error('not yet found'));
  button('Import prepared rows').click();
  await vi.waitFor(() => expect(container.textContent).toContain('Completion is not yet confirmed'));
  await router.push('/admin');
  expect(router.currentRoute.value.path).toBe('/admin/card-backs/import');
  expect(document.body.textContent).not.toContain('Discard this import draft?');
  get.mockResolvedValue({ data: { outcome: 'succeeded', asset: { id: 'new' }, hero_card_id: null } });
  button('Check / retry').click();
  await vi.waitFor(() => expect(container.textContent).toContain('Imported to library'));
  expect(post).toHaveBeenCalledTimes(1);
  expect(window.dispatchEvent(new Event('beforeunload', { cancelable: true }))).toBe(true);
  await router.push('/admin');
  expect(router.currentRoute.value.path).toBe('/admin');
});
