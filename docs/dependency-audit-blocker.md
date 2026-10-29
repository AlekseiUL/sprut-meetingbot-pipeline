# Dependency audit blocker

The TypeScript lint-toolchain repair is independent of a newly reported production dependency advisory. Do not deploy or merge this candidate while the audit gate is red.

GHSA-gcqx-w48m-w2h4 reports prototype poisoning in deepmerge 4.2.0 through 4.3.1. The public advisory, updated 2026-10-27, lists no patched version; the registry currently advertises 4.3.1 as latest.

Dependency path: puppeteer-extra-plugin-stealth 2.11.2 → puppeteer-extra-plugin-user-preferences 2.4.1 → deepmerge ^4.2.2. The preferences plugin invokes `merge` and `merge.all` when constructing user preferences. This is not fixed by updating the TypeScript parser or plugin. An older deepmerge override would violate the parent's declared range, and npm's proposed stealth downgrade changes runtime behavior; neither is applied.

The service is retired. This change only builds source, runs offline tests and builds containers without launching them. No meeting, browser, capture, authentication or cloud operation is executed. Both npm audit gates remain intact, at their existing severity thresholds, with no advisory suppression.

Resolution requires a verified upstream patch or a separately reviewed replacement of this dependency surface, with equivalent preference-merge behavior and prototype-poisoning regression tests. A successful build does not resolve this security blocker.

Reference: https://github.com/advisories/GHSA-gcqx-w48m-w2h4
