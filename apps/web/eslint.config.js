// Base rules + Vue. Prettier is applied last so it wins over eslint-plugin-vue's
// stylistic rules.
import pluginVue from 'eslint-plugin-vue';
import {
  defineConfigWithVueTs,
  vueTsConfigs,
} from '@vue/eslint-config-typescript';
import prettier from 'eslint-config-prettier';
import baseConfig from '../../eslint.config.base.js';

export default defineConfigWithVueTs(
  ...baseConfig,
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommendedTypeChecked,
  prettier,
);
