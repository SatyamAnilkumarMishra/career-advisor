// NOTE ON THE ESLINT VERSION
// `npm install` prints "npm warn deprecated eslint@9.x: This version is no
// longer supported" — eslint 9 is in maintenance mode now that 10 is out.
// Do NOT bump to eslint 10 yet: eslint-config-next@16.3.3 bundles
// eslint-plugin-react@7.37.x, whose `react/display-name` rule calls the eslint 9
// context API and throws under 10 ("contextOrFilename.getFilename is not a
// function"), which takes the whole lint run down. The warning is cosmetic;
// linting works correctly on 9.x. Revisit once eslint-config-next declares
// eslint 10 support in its peer dependencies.
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
