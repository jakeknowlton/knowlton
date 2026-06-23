// Lints the shared packages. apps/web has its own config (adds Vue) and
// apps/api is Python, so neither is linted here.
import baseConfig from './eslint.config.base.js';
import prettier from 'eslint-config-prettier';

export default [...baseConfig, prettier];
