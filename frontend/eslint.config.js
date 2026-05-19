import eslintPluginVue from 'eslint-plugin-vue';
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript';

export default defineConfigWithVueTs(
  {
    ignores: ['dist/**', 'coverage/**', 'test-results/**'],
  },
  eslintPluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
);
