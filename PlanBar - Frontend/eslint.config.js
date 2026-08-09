import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import reactPlugin from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import importPlugin from "eslint-plugin-import-x";
import prettierConfig from "eslint-config-prettier";

export default [
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
      react: reactPlugin,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      "import-x": importPlugin,
    },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react/prop-types": "off",
      "react/react-in-jsx-scope": "off",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-non-null-assertion": "warn",
      "max-lines-per-function": ["warn", { max: 80, skipComments: true, skipBlankLines: true }],
      "max-lines": ["warn", { max: 400, skipComments: true }],
      complexity: ["warn", 10],
      "max-params": ["warn", 4],
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-magic-numbers": ["warn", { ignore: [-1, 0, 1, 60, 24, 100] }],
      "import-x/order": ["warn", { "newlines-between": "always" }],
    },
    settings: { react: { version: "detect" } },
  },
  prettierConfig,
  {
    ignores: ["dist/**", "node_modules/**", "**/*.test.ts", "**/*.test.tsx"],
  },
];
