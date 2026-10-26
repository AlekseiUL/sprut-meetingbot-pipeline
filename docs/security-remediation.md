# Source-only security changes

Dispatch authentication is now mandatory before body parsing, route handlers, job creation or disk IO. All HTTP routes, including health/metrics/debug, require `Authorization: Bearer <dispatch token>`. The server reads `MEETINGBOT_DISPATCH_TOKEN` from its environment. The Python clients use the same environment setting, prohibit redirects and reject non-loopback plaintext HTTP. Existing unauthenticated clients must be upgraded. No credentials are bundled or generated.

Join requests are bounded to 16 KiB, provider HTTPS hosts and simple user IDs (`[A-Za-z0-9_-]`, 1–128 characters). These restrictions intentionally reject arbitrary URLs and path-like user IDs. Recording directories/files reject traversal and existing symlinks; writes use O_NOFOLLOW. The recording tree and its ancestors MUST be owned by the service and not writable by untrusted local users: these checks are not an atomic openat directory-handle sandbox against a hostile local process swapping parent directories. No cross-user authorization model is claimed for the shared dispatch token. Redis is disabled in the default deployment; enabling it requires a separate trusted-queue boundary review.

The logger redacts structured auth/config/request data and URLs; raw browser console content is omitted. This is a bounded logging improvement, not a guarantee that all third-party libraries redact every possible free-text secret.

## Dependencies

The lockfile was refreshed within compatible declared ranges. Unused direct Puppeteer and puppeteer-extra runtime packages were removed: the actual browser implementation uses Playwright-extra with the retained stealth plugin. No Puppeteer major upgrade was forced. GCS storage was explicitly upgraded from v7 to v8.4.0; the used constructor/bucket/file/save surface is covered with offline object-construction tests and TypeScript build. Actual cloud upload is not tested or authorized by these fixtures.

TypeScript is explicitly pinned to 5.9.3: leaving it as an unconstrained ts-node peer selected TypeScript 7, which broke ts-node's compiler API. Azure identity is pinned to 4.13.0 to avoid the newer MSAL authorization-code advisory; this retains a moderate UUID transitive advisory. The MSAL caller uses `uuid.v4()` without a supplied buffer, not the affected v3/v5/v6 buffer path (GHSA-w5hq-g745-h8pq). This is triage, not a claim of zero advisories; rerun `npm audit --omit=dev` before release. Do not force a transitive major UUID override merely to turn the audit green.

## Offline gate and rollback

Run `npm ci --ignore-scripts`, `npm run build`, and `node -r ts-node/register --test tests/*.cjs` in backend; run `python -m unittest discover -s tests -v` at repository root. These fixtures do not import the server entry point, start Docker, launch a meeting browser, record media or call cloud providers. Live browser compatibility and deployment health remain unverified.

Rollback is a new checkout of the previous source/lockfile plus `npm ci --ignore-scripts`; keep recording data untouched. Do not restore the unauthenticated network exposure as a rollout shortcut. A live rollout or repository archival requires a separate operator decision.
