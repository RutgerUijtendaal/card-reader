import eslintPluginVue from 'eslint-plugin-vue';
import boundaries from 'eslint-plugin-boundaries';
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript';
import { fileURLToPath } from 'node:url';

const frontendRoot = fileURLToPath(new URL('.', import.meta.url));

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
            {
              from: { element: { type: 'domain' } },
              allow: { to: { element: { types: ['domain', 'shared'] } } },
            },
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
