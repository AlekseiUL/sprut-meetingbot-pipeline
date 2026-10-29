# TypeScript ESLint maintenance

The parser and plugin are one toolchain: both are pinned to 8.72.0 with ESLint
8.57.1 and TypeScript 5.9.3. Their declared peer ranges are compatible. Dependabot
groups `@typescript-eslint/*`, including major proposals, so a parser-only major
upgrade cannot leave the plugin on an incompatible major. Proposals still
require manual review and all existing checks.

The migration explicitly preserves the previous v5.62 recommended severities
for `no-explicit-any` and `no-unused-vars` (warnings, not disabled). Source:
https://github.com/typescript-eslint/typescript-eslint/blob/v5.62.0/packages/eslint-plugin/src/configs/recommended.ts

The existing CommonJS fallback's targeted exception follows the rule rename
from `no-var-requires` to `no-require-imports`. No service behavior is changed.
`npm run lint` now reports warnings and never edits files; `npm run lint:fix`
is an explicit local action. CI adds lint without removing any prior gate.

Verification is source-only: npm ci, lint, TypeScript build, offline tests and
container builds. Never start the recording service for dependency acceptance.
A failing advisory audit is a release blocker, not permission to suppress an
advisory, downgrade packages blindly or bypass branch protection.
