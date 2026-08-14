import { createApp, h } from 'vue';
import { describe, expect, test } from 'vitest';
import TemplateRegionOverlay from '@/features/admin/components/TemplateRegionOverlay.vue';

describe('TemplateRegionOverlay', () => {
  test('renders name and affinity with explicit parser-type styles', () => {
    const container = document.createElement('div');
    const app = createApp({
      render: () => h(TemplateRegionOverlay, {
        regions: [
          {
            region_id: 'name_bar',
            parser_type: 'name',
            left_pct: 4,
            top_pct: 2,
            width_pct: 92,
            height_pct: 7,
          },
          {
            region_id: 'affinity_bar',
            parser_type: 'affinity',
            left_pct: 37,
            top_pct: 93,
            width_pct: 26,
            height_pct: 6,
          },
        ],
      }),
    });
    app.mount(container);

    expect(container.querySelector('.border-cyan-300')?.textContent).toContain('name_bar');
    expect(container.querySelector('.border-violet-300')?.textContent).toContain('affinity_bar');

    app.unmount();
  });
});
