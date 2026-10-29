# Vendored deepmerge security fork

This is a source-visible, private local fork, not an npm publication and not an
upstream security release. It fixes the returned-object prototype poisoning in
[GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4).

## Provenance

- Upstream: https://github.com/TehShrike/deepmerge
- Version: 4.3.1; commit `5b87756a5671635679001cbac72aa42f23472c81`.
- Source file: `package/dist/cjs.js` from
  https://registry.npmjs.org/deepmerge/-/deepmerge-4.3.1.tgz
- Verified tarball integrity:
  `sha512-3sUqbMEc77XqpdNO7FRyRog+eW3ph+GYCbj+rK+uYyRMuwsVy0rMiVtPn+QJlKFvWP/1PYpapqYn0Me2knFn+A==`.
- Original CJS SHA-256:
  `2e5160f84a1141bd927264afe4d15766f1e6cf07daef182b37ff53fea121de7d`.
- Original MIT copyright and license are preserved in `LICENSE`.

`index.cjs` is the upstream bundle with only `getKeys` changed: filter
`__proto__`, `constructor`, and `prototype` before reading their values.
Both target cloning and source merging use this function, including recursive
merges and the default array clone. Merely validating source keys against the
target is insufficient: an own enumerable `__proto__` in the target was also
assigned through the destination's inherited setter.

## Compatibility and scope

Keep `merge(target, source, options)`, `merge.all`, recursive precedence,
concatenating arrays, cloning, symbols, special values and the upstream
`arrayMerge`, `customMerge`, `isMergeableObject`, `clone` option contracts.
The intentional behavior change is dropping the three prototype-control keys
where the merger traverses an object. They are not supported preference keys.
The user-preferences and user-data-dir plugins themselves are unchanged.

This is not a general object sanitizer. Upstream `clone: false` and a custom
`isMergeableObject` can return input references without traversing them;
custom callbacks are trusted application code. Getters/proxies on ordinary
keys can still execute. Cyclic objects and arbitrary hostile JavaScript are
outside the JSON preference threat model. Do not claim generic sandboxing.

## Installation and verification

The backend pins a root `deepmerge` file dependency and uses the npm
`$deepmerge` override for transitive consumers. No install hook, runtime
monkeypatch, audit exclusion, forced install or plugin downgrade is used.
Both Dockerfiles copy `vendor` before `npm ci`.

From `backend`, under Node 24:

    npm ci
    npm ls deepmerge --all
    node --test tests/deepmerge-security.cjs
    npm run lint
    npm run build
    node -r ts-node/register --test tests/*.cjs
    npm audit --audit-level=low
    npm audit --omit=dev --audit-level=low

Tests resolve the merger through the real user-preferences package. They cover
source/target poisoning, nested arrays, blocked getters, API/options and actual
plugin dependency ordering, pre-launch dispatch and preference serialization
into a test-created temporary directory. They never launch a browser or service.

The fork's separate package identity makes npm audit insufficient evidence for
its code: security regression tests and review of the small upstream diff are
mandatory. Registry dependencies remain audited at every severity. A future
upstream replacement must pass these same tests before removing the vendor.
The project maintainer owns monitoring upstream advisories and this local fork.
Rollback is an ordinary revert commit/PR; reverting this security fix restores
the advisory and is not permission to deploy the vulnerable dependency.
