# Legacy minimatch API adapter

This repository-owned adapter replaces the minimatch 3 matching implementation;
it does not rename or relabel the old source. All compilation and matching use
unmodified upstream `minimatch@11.0.4`, installed through the transparent npm
alias `minimatch-engine`. The lock records the actual upstream name, tarball and
integrity. Upstream retains its Blue Oak license in the installed package; this
new adapter is MIT licensed under the repository license.

## Why it exists

[GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)
flags minimatch below 11.0.1. The current legacy parents do not accept 11's named
exports, and glob 7 expects regex-shaped segment objects. A bare major override
is not compatible. The adapter preserves the reviewed consumers' callable API
while using 11's nonrecursive matching engine and fixed preprocessing guards.
No audit exclusions or advisory severity changes are made.

`backend/package.json` limits the adapter override to minimatch **3.x**.
The locked consumers are ESLint 8.57.1, @eslint/eslintrc 2.1.4,
@humanwhocodes/config-array 0.13.0 and glob 7.2.3. The latter is used by rimraf 3
in the production user-data-dir cleanup chain and the development cache chain.
Nodemon 3.1.14 and typescript-estree 8.72.0 instead receive named-export upstream
11.0.4 through separate parent-scoped overrides. Nothing replaces all minimatch
majors globally. New consumers or parent upgrades require review and tests.

## Supported surface and deliberate boundary

- Callable `(path, pattern, options)`, callable/new `Minimatch`, `.match`,
  `filter`, `braceExpand`, `defaults`, `match` (including `nonull`), `sep`,
  `GLOBSTAR`, and the public fields read by the locked consumers.
- Legacy constructor whitespace trimming and pattern-length validation.
- Optimization level 0 by default, closest to the old path-segment behavior.
  Explicit level 2 still uses the **fixed upstream** guards; it is not disabled.
- Glob 7's `_glob` and `String.match(segment)` via `Symbol.match`, delegated to
  the upstream segment matcher. No regex compiler or old matching code is copied.

This is **not** a complete drop-in implementation of every minimatch 3 internal
API. `makeRe`, regex `.source`, `instanceof RegExp` for segments, and mutable
internal matcher state are not supported. The inspected consumers do not use
those surfaces. Matching semantics are now minimatch 11's, with the adaptations
above; arbitrary patterns and untested platforms are not claimed equivalent.
Do not add a consumer that needs an unsupported API without a new migration gate.

## Maintenance and verification

Run from `backend` on Node 24:

    npm ci --ignore-scripts
    npm run build
    node -r ts-node/register --test tests/*.cjs
    npm audit --audit-level=low
    npm audit --omit=dev --audit-level=low
    npm ls minimatch minimatch-engine --all

`tests/minimatch-compat.cjs` checks actual resolved consumers, old callable
positive/negative cases, bounded level-two amplification, glob sync/async paths,
rimraf callback and symlink safety, synthetic profile deletion/preservation,
ESLint file/override/flat-config paths, nodemon filtering and TypeScript project
service allowlists. Cleanup tests create and remove only disposable fixtures.
No service, watcher or browser is started.

Keep engine versions and integrity locked; audit the alias too. Remove this
adapter and its overrides only when the legacy parent chains support a patched
upstream API and the same tests pass. The repository maintainers own this small
compatibility surface; it is not a separately published security fork.

Rollback is an ordinary reviewed revert PR. Reverting restores the vulnerable
lock graph and therefore the red dependency audit; never suppress that gate.
