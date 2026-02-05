// ESLint flat config for ESLint 9+
// This config is compatible with Prettier and won't conflict with formatting rules

import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import importPlugin from 'eslint-plugin-import';
import prettierConfig from 'eslint-config-prettier';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default [
  // Base recommended rules
  js.configs.recommended,

  // Ignore patterns
  {
    ignores: [
      'node_modules/**',
      'skills/**',
      'skills-ts-out/**',
      'scripts/**',
      'examples/**',
      'skills-py/**',
      'dev/**',
      '*.config.js',
      '*.config.mjs',
      '*.config.ts',
      'tsconfig.tsbuildinfo',
    ],
  },

  // TypeScript files configuration
  {
    files: ['src/**/*.ts', 'types/**/*.ts'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './tsconfig.json',
        tsconfigRootDir: __dirname,
      },
      globals: {
        // QuickJS runtime globals
        console: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearTimeout: 'readonly',
        clearInterval: 'readonly',
        // Bridge API globals (defined in types/globals.d.ts)
        db: 'readonly',
        store: 'readonly',
        net: 'readonly',
        cron: 'readonly',
        skills: 'readonly',
        platform: 'readonly',
        state: 'readonly',
        data: 'readonly',
        tools: 'writable',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      import: importPlugin,
    },
    rules: {
      // Disable base no-unused-vars in favor of TypeScript version
      'no-unused-vars': 'off',
      // TypeScript recommended rules
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_|^[A-Z_]+$', // Ignore _prefixed vars and ALL_CAPS (enum members)
          caughtErrorsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',

      // Import/export rules
      'import/order': 'off', // Prettier plugin handles import sorting
      'import/no-unresolved': 'off', // TypeScript handles this
      'import/no-cycle': 'warn',
      'import/no-duplicates': 'error',

      // General JavaScript/TypeScript rules
      'no-console': 'off', // Allow console in skills
      'no-debugger': 'error',
      'no-duplicate-imports': 'error',
      'no-unused-expressions': 'off', // Covered by @typescript-eslint version
      '@typescript-eslint/no-unused-expressions': 'error',

      // Code quality
      'prefer-const': 'error',
      'no-var': 'error',
      'object-shorthand': 'error',
      'prefer-arrow-callback': 'error',

      // Style: Enforce single-line statements on same line without braces when possible
      curly: ['error', 'multi', 'consistent'],
      'nonblock-statement-body-position': ['error', 'beside'],
    },
  },

  // Test files configuration
  {
    files: ['**/__tests__/**/*.ts', '**/*.test.ts', '**/*.spec.ts'],
    languageOptions: {
      globals: {
        // Test harness globals
        _describe: 'readonly',
        _it: 'readonly',
        _assertEqual: 'readonly',
        _assertNotNull: 'readonly',
        _assertNull: 'readonly',
        _assertTrue: 'readonly',
        _assertFalse: 'readonly',
        setupSkillTest: 'readonly',
        callTool: 'readonly',
        getMockState: 'readonly',
        mockFetchResponse: 'readonly',
        mockFetchError: 'readonly',
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'off', // Allow any in tests
      '@typescript-eslint/no-non-null-assertion': 'off', // Allow non-null assertions in tests
    },
  },

  // JavaScript files configuration
  {
    files: ['**/*.js', '**/*.mjs'],
    languageOptions: { ecmaVersion: 'latest', sourceType: 'module' },
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-console': 'off',
      'no-debugger': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
    },
  },

  // Disable all Prettier-conflicting rules (must be last)
  prettierConfig,
];
