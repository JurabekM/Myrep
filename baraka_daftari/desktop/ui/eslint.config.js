import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'src/bindings'] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Frontend pul hisoblamaydi: Number() bilan summa parse qilish taqiqlanadi.
      'no-restricted-globals': ['error', 'parseFloat'],
      // Tauri commandlari faqat generatsiya qilingan bindings orqali.
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@tauri-apps/api/core',
              message: "invoke() qo'lda chaqirilmaydi: src/bindings dan foydalaning.",
            },
          ],
        },
      ],
    },
  },
  { files: ['*.config.{ts,js}'], ...tseslint.configs.disableTypeChecked },
);
