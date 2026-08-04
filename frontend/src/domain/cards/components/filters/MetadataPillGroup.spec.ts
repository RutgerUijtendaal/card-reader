import { createApp, defineComponent, h, nextTick, ref } from 'vue';
import { afterEach, describe, expect, test } from 'vitest';
import MetadataPillGroup, {
  type MetadataPillOptionGroup,
} from '@/domain/cards/components/filters/MetadataPillGroup.vue';
import type { MetadataOption } from '@/domain/cards/types';

const options: MetadataOption[] = [
  { id: 'option-1', key: 'alpha', label: 'Alpha' },
  { id: 'option-2', key: 'beta', label: 'Beta' },
  { id: 'option-3', key: 'gamma', label: 'Gamma' },
  { id: 'option-4', key: 'delta', label: 'Delta' },
];

const mountPills = async ({
  initialIncluded = [],
  initialExcluded = [],
  groups = [],
  initialVisibleCount = 10,
}: {
  initialIncluded?: string[];
  initialExcluded?: string[];
  groups?: MetadataPillOptionGroup[];
  initialVisibleCount?: number;
} = {}) => {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const included = ref([...initialIncluded]);
  const excluded = ref([...initialExcluded]);

  const Root = defineComponent({
    setup() {
      return () =>
        h(MetadataPillGroup, {
          label: 'Types',
          options,
          includedValue: included.value,
          excludedValue: excluded.value,
          matchMode: 'any',
          defaultOpen: true,
          initialVisibleCount,
          groups,
          'onUpdate:includedValue': (value: string[]) => {
            included.value = value;
          },
          'onUpdate:excludedValue': (value: string[]) => {
            excluded.value = value;
          },
          onReset: () => {
            included.value = [];
            excluded.value = [];
          },
        });
    },
  });

  const app = createApp(Root);
  app.mount(container);
  await nextTick();

  return {
    container,
    included,
    excluded,
    unmount: () => {
      app.unmount();
      container.remove();
    },
  };
};

const findOptionButton = (container: HTMLElement, label: string): HTMLButtonElement => {
  const button = Array.from(container.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.getAttribute('aria-label')?.startsWith(`${label} `),
  );
  if (!button) {
    throw new Error(`expected ${label} option button`);
  }
  return button;
};

describe('MetadataPillGroup', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  test('cycles pills through include, exclude, and off states', async () => {
    const mounted = await mountPills();
    let button = findOptionButton(mounted.container, 'Alpha');

    expect(button.getAttribute('aria-label')).toBe('Alpha not filtered. Click to include.');

    button.click();
    await nextTick();
    button = findOptionButton(mounted.container, 'Alpha');
    expect(mounted.included.value).toEqual(['option-1']);
    expect(mounted.excluded.value).toEqual([]);
    expect(button.classList.contains('theme-choice-chip-include')).toBe(true);
    expect(button.textContent).toContain('+');
    expect(button.getAttribute('aria-label')).toBe('Alpha included. Click to exclude.');

    button.click();
    await nextTick();
    button = findOptionButton(mounted.container, 'Alpha');
    expect(mounted.included.value).toEqual([]);
    expect(mounted.excluded.value).toEqual(['option-1']);
    expect(button.classList.contains('theme-choice-chip-exclude')).toBe(true);
    expect(button.textContent).toContain('−');
    expect(button.getAttribute('aria-label')).toBe('Alpha excluded. Click to clear.');

    button.click();
    await nextTick();
    button = findOptionButton(mounted.container, 'Alpha');
    expect(mounted.included.value).toEqual([]);
    expect(mounted.excluded.value).toEqual([]);
    expect(button.getAttribute('aria-pressed')).toBe('false');

    mounted.unmount();
  });

  test('keeps excluded collapsed options visible and resets both state buckets', async () => {
    const mounted = await mountPills({
      initialIncluded: ['option-1'],
      initialExcluded: ['option-4'],
      initialVisibleCount: 2,
    });

    expect(findOptionButton(mounted.container, 'Delta')).toBeInstanceOf(HTMLButtonElement);
    expect(mounted.container.textContent).toContain('+1');
    expect(mounted.container.textContent).toContain('-1');

    const reset = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Reset group"]',
    );
    reset?.click();
    await nextTick();

    expect(mounted.included.value).toEqual([]);
    expect(mounted.excluded.value).toEqual([]);

    mounted.unmount();
  });

  test('preserves group-specific include colors and uses the shared exclude color', async () => {
    const mounted = await mountPills({
      groups: [
        {
          key: 'roles',
          label: 'Roles',
          options: [options[0]!],
          selectedClass: 'theme-choice-chip-accent shadow-sm',
        },
        {
          key: 'types',
          label: 'Types',
          options: [options[1]!],
          selectedClass: 'theme-choice-chip-keyword shadow-sm',
        },
      ],
    });

    let roleButton = findOptionButton(mounted.container, 'Alpha');
    roleButton.click();
    await nextTick();
    roleButton = findOptionButton(mounted.container, 'Alpha');
    expect(roleButton.classList.contains('theme-choice-chip-accent')).toBe(true);

    roleButton.click();
    await nextTick();
    roleButton = findOptionButton(mounted.container, 'Alpha');
    expect(roleButton.classList.contains('theme-choice-chip-exclude')).toBe(true);
    expect(roleButton.classList.contains('theme-choice-chip-accent')).toBe(false);

    mounted.unmount();
  });
});
