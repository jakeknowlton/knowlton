// Shared ESLint base for all TypeScript in the monorepo. Stylistic rules are
// left to Prettier (eslint-config-prettier is applied last by each consumer).
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import globals from 'globals';
import { defineConfig } from 'eslint/config';

export default defineConfig(
  {
    ignores: ['**/dist/**', '**/node_modules/**', '**/generated.ts'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node },
      parserOptions: {
        projectService: true,
        // Anchored to this file (not the cwd) so type-aware linting resolves
        // correctly whichever workspace imports this base.
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],

      // Stricter rules layered on top of recommendedTypeChecked.
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/no-unnecessary-condition': 'error',
      // allowNullableBoolean: permit bare truthy checks on `boolean | null
      // | undefined` (e.g. `!flag`).
      '@typescript-eslint/strict-boolean-expressions': [
        'error',
        { allowNullableBoolean: true },
      ],
      '@typescript-eslint/no-confusing-void-expression': 'error',
    },
  },
  {
    // Config files sit outside any tsconfig, so type-aware rules can't run.
    files: ['**/*.{js,cjs,mjs}'],
    extends: [tseslint.configs.disableTypeChecked],
  },
);
