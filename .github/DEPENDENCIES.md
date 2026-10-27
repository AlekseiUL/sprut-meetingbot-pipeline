# Dependency maintenance

Dependabot opens weekly review-first pull requests for the applicable manifests and GitHub Actions. There is no auto-merge. Keep existing SHA pins and review upstream changes before accepting updates.

The weekly dependency-audit workflow blocks every advisory in `requirements-audit.txt`, a complete pinned dependency snapshot (Python 3.12). It uses `pip-audit --strict --disable-pip --no-deps`; no target package is installed or executed by this audit. Runtime, optional and build/test dependencies are included where declared. This snapshot is not a claim about arbitrary caller-installed packages or optional external services.

Regenerate the snapshot when a dependency manifest changes. Review the diff, run the audit and the full regression/install gate before merging. Keep the snapshot aligned with the existing uv.lock/requirements-ci.lock when present. Do not suppress advisories to obtain green CI.

The ASR snapshot targets Apple Silicon/macOS 14+ and Python 3.12; newer patched torch wheels require macOS 14+. ASR/model downloads and live recording are not part of this gate. Node is 24 LTS in CI and both Debian bookworm Dockerfiles. Container builds require an available Docker builder; source tests alone do not prove container viability.

The npm lockfile is audited for production and development at `--audit-level=low`: all known advisories block CI. The existing production-only MeetingBot gate is not weakened. Node 24 LTS is the tested runtime.
