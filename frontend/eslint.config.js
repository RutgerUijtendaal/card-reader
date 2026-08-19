import eslintPluginVue from 'eslint-plugin-vue';
import boundaries from 'eslint-plugin-boundaries';
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript';
import { fileURLToPath } from 'node:url';

const frontendRoot = fileURLToPath(new URL('.', import.meta.url));

export const domainDependencies = {
  'access-requests': ['session'],
  'card-backs': ['cards'],
  'card-deck-references': ['card-navigation', 'decks'],
  'card-navigation': ['cards', 'decks', 'notifications'],
  cards: ['deck-building'],
  'deck-building': [],
  decks: ['card-backs', 'cards', 'deck-building'],
  'developer-data': [],
  maintenance: [],
  notifications: ['session'],
  operations: [],
  review: ['cards', 'session'],
  session: ['cards'],
  templates: ['cards', 'maintenance'],
};

export const assertDomainDependencyGraph = (dependencies) => {
  const slices = new Set(Object.keys(dependencies));
  const visiting = new Set();
  const visited = new Set();

  const visit = (slice, path) => {
    if (visiting.has(slice)) {
      throw new Error(`Circular frontend domain dependency: ${[...path, slice].join(' -> ')}`);
    }
    if (visited.has(slice)) return;

    visiting.add(slice);
    for (const dependency of dependencies[slice]) {
      if (!slices.has(dependency)) {
        throw new Error(`Unknown frontend domain dependency: ${slice} -> ${dependency}`);
      }
      if (dependency === slice) {
        throw new Error(`Frontend domain cannot depend on itself: ${slice}`);
      }
      visit(dependency, [...path, slice]);
    }
    visiting.delete(slice);
    visited.add(slice);
  };

  for (const slice of slices) visit(slice, []);
};

assertDomainDependencyGraph(domainDependencies);

const domainDependencyPolicies = Object.entries(domainDependencies).map(([slice, allowedDomains]) => ({
  from: { element: { type: 'domain', captured: { slice } } },
  allow: {
    to: {
      element: [
        { type: 'shared' },
        ...allowedDomains.map((allowedSlice) => ({
          type: 'domain',
          captured: { slice: allowedSlice },
        })),
      ],
    },
  },
}));

export default defineConfigWithVueTs(
  {
    ignores: ['dist/**', 'coverage/**', 'test-results/**'],
  },
  eslintPluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  {
    plugins: {
      boundaries,
    },
    settings: {
      'import/resolver': {
        typescript: {
          project: fileURLToPath(new URL('./tsconfig.json', import.meta.url)),
        },
      },
      'boundaries/root-path': frontendRoot,
      'boundaries/legacy-templates': false,
      'boundaries/elements': [
        { type: 'app', pattern: 'src/app', partialMatch: false },
        {
          type: 'feature',
          pattern: 'src/features/*',
          capture: ['slice'],
          partialMatch: false,
        },
        {
          type: 'domain',
          pattern: 'src/domain/*',
          capture: ['slice'],
          partialMatch: false,
        },
        { type: 'shared', pattern: 'src/shared', partialMatch: false },
      ],
    },
    rules: {
      'boundaries/dependencies': [
        'error',
        {
          default: 'disallow',
          policies: [
            {
              from: { element: { type: 'app' } },
              allow: {
                to: { element: { types: ['app', 'feature', 'domain', 'shared'] } },
              },
            },
            {
              from: { element: { type: 'feature' } },
              allow: { to: { element: { types: ['domain', 'shared'] } } },
            },
            ...domainDependencyPolicies,
            {
              from: { element: { type: 'shared' } },
              allow: { to: { element: { type: 'shared' } } },
            },
          ],
        },
      ],
      'boundaries/no-unknown-files': 'error',
    },
  },
);
