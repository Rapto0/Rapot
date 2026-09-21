# Verified commit → Docker Compose

Supported production topology: Compose 2.24+, Python 3.12.8 with runtime dependencies
constrained by `requirements-dev.lock`, Node 20.20.2/npm 10.9.9 and Next.js standalone.
Unused legacy PM2/API launcher files were removed in the 21 September repository cleanup.
Docker Compose is the supported production path; historical cutover evidence remains below.

## Services

| Service | Host endpoint | Storage/start condition |
|---|---|---|
| main-init | none | Main SQLite schema preparation via existing `db_session.init_db` policy |
| api | 127.0.0.1:8000 | main-init success; one worker; embedded bot disabled |
| bot | 127.0.0.1:5000 health | main-init + API health; one scanner with lifetime process lock |
| frontend | 127.0.0.1:3000 | API health; standalone output |
| postgres | internal only | Optional middleware profile; dedicated named volume |
| middleware-migrate | none | PostgreSQL health; Alembic upgrade |
| middleware | 127.0.0.1:8001 | Migration success and current revision check |

API, bot and main-init share the **directory** `RAPOT_DATA_DIR` (default `./runtime-data`),
including `trading_bot.db`, `price_cache.db`, SQLite WAL/SHM files and the bot lock. Code
comes from images, without a source bind mount. Direct and embedded `scheduler.start_bot`
calls use the same database-derived lock; if working directories or database URLs differ,
set `BOT_LOCK_PATH` to the same shared file. Do not delete a live lock file.

Middleware never mounts the main SQLite directory. Its optional profile pins DRY_RUN,
trading disabled and live adapter disabled. Deployment does not enable or send broker orders.

## First cutover from the old layout

The verified target is `root@138.68.71.27`, with releases under `/opt/rapot/releases`
and `/opt/rapot/current` selecting the active release. The original `/root/Rapot` checkout
is retained as history. P1-2 cutover and HTTPS were verified after SSH access was restored;
see [the current release and evidence record](RAPOT_DEVAM_PLANI.md). Keep private
keys and passwords outside reports. The following checklist describes the initial cutover.

1. Record server commit, checkout changes, PM2/systemd/nohup processes, listening ports,
   actual data paths and reverse proxy. Do not stop unidentified processes.
2. Back up SQLite with its backup API, or stop identified writers before copying the database
   and WAL state. Back up any middleware database separately.
3. Prepare an absolute `RAPOT_DATA_DIR` with the reviewed DB/cache. Compose never moves
   root-level databases or selects among old copies. The release helper requires an existing
   main DB; `RAPOT_ALLOW_EMPTY_DATA=1` is only for a deliberately new empty installation.
4. Stop identified legacy Rapot writers during cutover. Old code predating the new file lock
   is not protected by it. Keep secrets in `.env` or `RAPOT_MAIN_ENV_FILE`, outside Git/images.
5. Expose the frontend through the reviewed HTTPS reverse proxy, including WebSocket Upgrade
   headers. Backend ports bind to loopback. A public webhook route must not expose middleware
   management paths. Verify P0-2 login/admin configuration before publishing.

Host Nginx upstreams must explicitly use `127.0.0.1` for ports 3000, 8000, 5000 and 8001,
matching the Compose bindings. `localhost` can resolve to `::1`, where these services do
not listen, causing intermittent 502 responses even when containers are healthy. Preserve
each location's existing path/trailing-slash and WebSocket behavior when changing the host.
Back up the active configuration, run `nginx -t`, reload Nginx, then verify public HTTPS
routes. On this VPS, the reviewed configuration is `/etc/nginx/sites-available/default`.

Frontend image builds use `API_PROXY_TARGET=http://api:8000` and
`HEALTH_PROXY_TARGET=http://bot:5000`; changing these targets requires a rebuild. Browser HTTP
and WebSockets use `/api`, health uses `/health-api`. Local npm builds default to localhost
8000/5000. These defaults must not be confused with container-local localhost.

## Release

Complete tests, lint/types, builds and required CI for the exact commit. P1-7 and P1-2
initial-release checks are recorded as complete in the plan. `scripts/deploy.ps1` checks
clean tree/branch/full SHA, optionally pushes, then prints server commands. It does not stage, commit, stash, reset
or connect over SSH. Supplying a SHA does not run or replace the release checks.

```powershell
$releaseCommit = git rev-parse HEAD
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -VerifiedCommit $releaseCommit
# Optional, only after release checks:
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1 -VerifiedCommit $releaseCommit -Push -IncludeMiddleware
```

The generated preflight is read-only. The deployment block rejects dirty checkouts, changed
remote SHAs, incompatible branches, legacy supervisors and unknown port owners. It updates
by fast-forward only, builds and starts services with health waits, then checks SHA/health.
A push or printed command list is not a successful server deployment.

After the cutover/data checks and exact server checkout:

```bash
export RAPOT_DATA_DIR=/absolute/reviewed/rapot-data
export RAPOT_RELEASE="$(git rev-parse HEAD)"
docker compose config --quiet
docker compose build api bot frontend
docker compose up -d --wait --wait-timeout 180 api bot frontend
docker compose ps --all
docker compose logs --tail 100 api bot frontend
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:5000/health
curl --fail --output /dev/null http://127.0.0.1:3000/
```

Also verify authenticated UI and WebSockets through the real reverse proxy. Record full
server SHA, image IDs and services. Local health alone does not prove TLS/login/webhook routing.
Bot database health can become ready before scheduler startup finishes. Separately verify
`/health-api/status` reports `bot.state=running` with `state_source=local_lifecycle`.
The P1-6 operator allows 180 seconds for this startup observation, with status requests
bounded to seven seconds; it retains the separate 20-second API health request limit.
This observation allowance is not a guarantee that startup finishes within 180 seconds.

### Frontend-only releases on the current VPS

The historical P2-1 archive procedure below applies to changes confined to frontend
application code and release documentation: its exact source diff requires backend code,
Compose, lock files and build inputs to remain unchanged. The separately reviewed P1-G2
dependency rollout below has its own source manifest and acceptance gates.
The P2-1 operator uses a source archive under `/opt/rapot/releases/<sha>` and the existing
private `/etc/rapot` environment files plus `compose.images.yml` digest overrides. It pulls
only the verified frontend digest, then runs Compose with the explicit project/environment/
override files and `up -d --no-deps --no-build --pull never frontend`. It does not run
initializers, migrations or restart API, bot, middleware or PostgreSQL.

The `current` source symlink and frontend OCI revision can advance while backend images and
`release.env`'s `RAPOT_RELEASE` remain at the previous backend SHA. Record
`release_source_sha`, `frontend_source_sha`, `backend_source_sha` and both image digests
separately; a single current symlink is not evidence that every service runs that revision.
Before and after the rollout, compare protected container IDs, image IDs, start times,
restart counts, environment file bytes and Nginx configuration. Preserve the prior frontend
digest/source and private config backup for frontend-only rollback. Do not restore databases
for a frontend failure. Local mocked interaction tests, external HTTPS/SSR checks and the
unchanged backend health checks are separate acceptance evidence.

## P2-3 rollout evidence — 11 September 2026

Application source `bacbfab814bb659f093a33733934b56f2bf5b19a` passed
[CI 34636602751](https://github.com/Rapto0/Rapot/actions/runs/34636602751) and
[image publication 34637100266](https://github.com/Rapto0/Rapot/actions/runs/34637100266).
The full API/bot/frontend/middleware rollout was verified at **19:14:51 UTC**.
All four application services now use that source; PostgreSQL was not recreated.

| Image | Immutable registry digest |
|---|---|
| Backend | `sha256:18dcf104fd3e3e85d6d016c22d76a98e6dbf88ae4e0a9b60554803468d0c81b4` |
| Frontend | `sha256:369674a790d86d84ee06e16edc050e2968d5928f511a31f666d5644ecfb65340` |

Evidence is retained in `/root/rapot-ops/20260911-p23/`: source preparation,
`deployment.json`, private configuration backups, and the independently verified
`trading_bot.before.sql.gz`. The SQL gzip is **135,495,129 bytes** with SHA256
`1ccfea7dbd37e632193e91d697a0fa80318fa251ad7d4e82149877376685d45c`.
A fresh read-only SQLite transaction bound the schema, metadata, typed row fingerprints
and SQL stream to one snapshot. Its independent private local restore passed integrity
and logical comparison for all **7 tables**; the restored file is **1,019,465,728 bytes**.
The physical size/hash differs from the source database and is not the comparison contract.
The additional PostgreSQL dump is **59,240 bytes** and its archive catalog was checked;
no independent PostgreSQL restore was performed in this rollout.

The first operator attempt rejected only the nonexecuted `x-python.image` template tag
comparison, before any pull or service change. Its three preparation records remain in
`attempt-1/`; the narrowly corrected operator completed the second attempt. Source
Compose, `db_session.py` and the entire Alembic chain were unchanged. No manual
initializer, migration, backfill or database restore was executed.

API startup preserved the six main application table counts; they also matched after
bot startup. PostgreSQL container ID/start time and counts **135/135/28/383** were unchanged.
All five services were healthy with restart count zero. HTTPS `/api/health` returned 200
in **0.036 s**; `/`, `/signals`, `/alarms`, `/chart` returned HTML/200. The shared signal
feed was ready, Binance/BIST providers reported started, and the scheduler reached its
local `running` lifecycle after **43.781 s** of observation. This does not establish a
completed fresh market scan, interactive browser acceptance, or a load benchmark.
An independent HTTPS check from the local Windows host at **19:19:35 UTC** returned
healthy/200 for API (**0.204 s**) and bot (**0.187 s**); these are separate observations.

Credentials, Nginx and DRY_RUN/trading=false/live=false were preserved. No testnet/live
orders or external AI/Telegram tests were sent. Old source trees, images and backups
remain; free disk after acceptance was **884,736,000 bytes**. Recheck capacity before
the next rollout. P1-G1 dependency-advisory triage and P2-4 concurrent-load latency remain
open; security findings are report-only, with full reports retained.
The nine exact-CI report/manifest/log files were copied and hash-verified under
`security-reports/`, so advisory triage does not depend on GitHub's 14-day artifact retention.

The final plan/deploy documentation commit is recorded separately in
`documentation-release-record.json`, with canonical Git blob hashes under `documents-final/`.
That documentation publication requires its own successful exact-SHA CI and does not
change the running application source, images, database or service lifecycle.

## P1-G1 rollout evidence — 11 September 2026

The dependency-security release **ccd61544ede603eb064d871a4ec797c5057307f4** was
verified in production at **20:56:32 UTC**, replacing `bacbfab8` for API, bot,
middleware and frontend. [CI 34641121926](https://github.com/Rapto0/Rapot/actions/runs/34641121926)
and [image publication 34641767731](https://github.com/Rapto0/Rapot/actions/runs/34641767731)
passed. The application source, configuration and acceptance record are retained in
`/root/rapot-ops/20260911-p1g1/`; `deployment.json` has status `verified` and SHA256
`f3d9444edf4484b4f42e81508b9425823f24b4af599af42218629e21f3a15fc2`.

| Component | Immutable image reference |
|---|---|
| Backend | `ghcr.io/rapto0/rapot/backend@sha256:0a92fc448e73134d82450c277219d2db82776ec6c9d4aa36c5a6ed5b7665ee39` |
| Frontend | `ghcr.io/rapto0/rapot/frontend@sha256:80145f4222058ef16e3dcc73a1f7dd002d07593d42db3c94dc57a73e76a5bda4` |

Local and Linux CI ran **710 Python tests without warnings**; the exact **115-package**
security inventory had zero known pip-audit advisories at the recorded scan. Bandit
still had 15 MEDIUM and 1,534 LOW findings; security remains report-only. This is not
an assertion that the operating-system image or application has no vulnerabilities.
The patch replaced python-jose with PyJWT HS256/required expiry, removed the unused
Streamlit branch and applied reviewed compatible dependency fixes. Schema, Compose
topology and the Alembic chain were unchanged; no manual initializer, migration,
backfill or production database restore was run.

The user rejected a paid server upgrade. After durable private copies and repeated
SHA/CRC/SQLite/ACL verification, the user's direct continuation authorized only the
three named historical gzip server copies listed in the
[continuation archive](archive/RAPOT_DEVAM_GECMISI_2026-09-21.md#p1-g1--python-bağımlılık-güvenliği).
Their removal is audited in
`/root/rapot-ops/p1g1-cold-retirement-5e4659d7a3e64888ae7405e9062680a0/`.
Observed free space increased by **606,547,968 bytes**. The six local files under
`C:\Users\memet\RapotBackups\20260911-p1g1-cold`, P2-3/P1-6 server backups and all
rollback images/releases were retained. This is no general cleanup authorization.

A new fixed-read-transaction SQL gzip snapshot was independently restored locally:
archive **135,547,494 bytes**, SHA256
`0d3036738f5acc171eca64a996849e709afd1312c0ab80543426d06a361a5e5c`.
Integrity, schema/pragmas and typed row fingerprints matched for all seven tables,
including legacy `lost_and_found`; the restored file is **1,019,871,232 bytes**.
The extra PostgreSQL custom dump is **59,240 bytes**, SHA256
`599993412c9b28dd21a2a14ab81eb27106569fad0459d374842e778e01c5fa71`;
its 66-line catalog was checked, but no independent PostgreSQL restore was performed.

Verified OCI blob/diffID measurements budgeted the remaining image cost plus
400 MiB reserve and 128 MiB growth allowance before each pull. Backend first shared
six layers; frontend shared all 13 layers. Every capacity gate passed; no old image
was pruned. Free space after acceptance was **724,676,608 bytes (~691 MiB)**.
These are checkpoint measurements, not a continuously measured peak. The next rollout
must recalculate available capacity; a paid upgrade remains unauthorized.

All five containers were healthy with zero restarts. Main counts before/after were
signals **1,733,137**, scan_history **6**, ai_analyses **26,393**, bot_stats **4** and
trades/orders **0/0**. PostgreSQL identity/start time and **135/135/28/383** counts
were unchanged. HTTPS health returned 200 in 0.047 s; `/`, `/signals`, `/alarms`
and `/chart` returned HTML/200. SignalFeed/providers were ready, and the scheduler
reached `running` after **47.298 s**. Separate Windows HTTPS API and bot probes each
returned healthy/200 in 0.203 s. No new full-scan, interactive-browser or load
acceptance is implied.

The rollback-protected auth acceptance passed **13/13 cases**: readiness, anonymous
and invalid-bearer 401 boundaries, unauthorized empty webhook 401 boundaries, and
existing admin/user login and identity. Admin `logs?limit=0` reached 422 validation;
the normal user received 403. Credentials/tokens stayed in RAM and were excluded
from result logs; no account was created. Old jose-token compatibility remains a
local/Linux test result, not a separately exercised live-session claim.
Credentials/Nginx, DRY_RUN/trading=false/live=false and disabled AI were preserved.
No testnet/live order or external AI/Telegram test was sent. P1-G1 is complete;
P2-4 latency and the deferred TradingView/alarm/order acceptance remain open.

The nine exact-code-CI report/provenance files were hash-verified under `security-reports/`;
`security-publication.json` retains source/artifact identity independently of GitHub artifact
retention. No runtime database or environment file was included.

The final documentation commit/CI and canonical Git blob checksums are recorded
separately in `documentation-release-record.json` and `documents-final/` under the
same OPS directory. Publishing these two documents does not restart the application
or alter images, configuration or databases.

## P2-4 production follow-up: tag query index

The first `aadde728f7e83a636b9493b660fed33434564e9a` rollout passed service,
HTTPS/SSR, data preservation and 13 auth checks on 13 September. Concurrent reads
still timed out on the BELES/COK_UCUZ lists; this rollout did not close P2-4.
The old plan used the single-column tag index followed by a temporary date sort.
The follow-up adds only the partial `(special_tag, created_at)` index for non-NULL
tags. Total signal counts remain exact: NULL and non-NULL partitions are counted
in the same SQL statement using covering tag indexes. No response cache or
restricted history window is introduced. Equal timestamps retain the existing
unspecified tie order; an index change can alter which tied rows enter a LIMIT.

This is an additive main SQLite index change, not a middleware Alembic revision.
Verify the exact new/old source and index definition, take a fresh independently
restored SQLite backup and a separate PostgreSQL dump, and include index creation
in the disk/WAL budget. Stop the main writers before the reviewed startup step.
Compare schema objects before/after: only `idx_signals_special_tag_created` may be
added; table contents, columns and PostgreSQL identity must be preserved. A code
rollback retains this compatible index and never restores or downgrades live data.
The prior operator's blanket no-schema-change check must not be disabled generally.

With limited VPS space, the reviewed fixed SQLite read transaction may stream its
SQL gzip directly to the operator's private computer instead of retaining another
large VPS archive. Both ends must verify the complete compressed hash/byte count;
the source SQL hash, snapshot schema/pragma and typed row fingerprints must match
an independent full restore. Retain the source manifest, private archive and restore
proof, bind their hashes to the exact rollout, and verify the private copy again
before cutover. A truncated stream or missing offhost proof blocks deployment.
Keep time, compressed-size, WAL-growth and disk-reserve guards active even under
network backpressure. The PostgreSQL dump remains separate; catalogue validation
and offhost copy hashes do not claim an independent PostgreSQL restore.

Production acceptance keeps its preselected bounds: three signals WSS connections,
three waves of eight representative REST reads, REST p95 below 5 s, WSS opening
below 3 s, protocol ping/pong p95 below 1 s and application heartbeat below 35 s.
These small-sample smoke checks are distinct from the isolated 250/500 ms benchmark
and are not a production SLA. Record all failures, application heartbeat/REST
overlap and socket cleanup; do not raise thresholds to conceal a failed run.
The current final deployment result is recorded in the continuation plan and the
versioned operator evidence, rather than inferred from published images.

### Verified index rollout — 13 September 2026

Source `279aa9fea99b520e661b43f104a2bf4791893ac3` passed
[CI 34745255161](https://github.com/Rapto0/Rapot/actions/runs/34745255161) and
[image publication 34745419330](https://github.com/Rapto0/Rapot/actions/runs/34745419330).
The deployment was verified at **07:44:25 UTC**, followed by successful bounded
concurrent-read acceptance at **07:45:19 UTC**. Evidence belongs to
`/root/rapot-ops/20260913-p24-index/`; local result copies are
`runtime-data/p24-index-deployment.json` and
`runtime-data/p24-index-production-read-acceptance.json`.
Backend digest is `sha256:9be0fdb6097f52bf97730f44c86d28c24e2c0cea1fe181e7e8fd668177fdb034`;
frontend digest is `sha256:e1e3702c591dd7f94793d93e0f1015310013a3233a0430087084db9d79327972`.

The fresh **07:24:47 UTC** SQLite snapshot streamed directly to private offhost
storage: **136,013,613 bytes**, SHA256
`2e7eb8f3b6765be5451333a3c4e494551661cb2964184065d221ed9f0eb299d6`.
Independent full restore and comparison passed in **69.66 s**; no SQLite archive
was retained on the VPS. The source archive was size/hash/CRC checked in bounded
RAM before extraction. Every capacity gate retained the 400 MiB reserve,
128 MiB growth margin and, until schema verification, a 16 MiB index-build allowance.
Final deployment free space was **580,993,024 bytes**. These are checkpoint
observations; neither a continuous disk peak nor future rollout capacity is implied.

Only `idx_signals_special_tag_created` was added to the main schema. Before/after
counts remained signals **1,740,288**, trades/orders **0/0**, scan_history **13**,
ai_analyses **26,393** and bot_stats **5**. PostgreSQL container identity and
**135/135/28/383** counts were preserved. All five containers were healthy with
zero restarts; HTTPS/SSR, feed/provider readiness, scheduler and **13/13 auth cases**
passed. Credentials/Nginx, disabled AI and DRY_RUN/trading=false/live=false were
preserved. Previous images, source, backups and the compatible rollback path remain.

The unchanged production bounds passed for **24 measured REST reads and three
signals WSS connections**. Nearest-rank p95 values were health **313 ms**,
BELES/COK_UCUZ **594/469 ms**, stats **2,438 ms**, WSS opening **516 ms**, and
protocol ping/pong **63 ms** across 162 samples. All three application heartbeats
arrived about 30 s after opening; one overlapped a REST read. All three test sockets
closed, signals-channel counts returned **1 → 1**, and runtime source/container/config
identity was unchanged. Initial failures remain separate evidence. These three
samples per REST route close the defined P2-4 smoke acceptance, not a production
SLA, continuous signal-delivery guarantee or full browser/load test. No testnet/live
order, actual TradingView alert delivery or external AI/Telegram test was performed;
those deferred checks and P3 work remain separate.

Record the final documentation commit/CI and canonical blob hashes separately
in this OPS directory's `documentation-release-record.json`. Documentation-only
publication does not rebuild images, restart services or change the database.

## Frontend-only component rollout — P3-1 first step, verified

The first P3-1 COMBO change preserves measured zero and excludes unavailable or
non-finite components from voting. Six new regressions and **105 frontend tests**
passed locally. Source `967f137351290735d7e6ae556b4ad237c253677c` passed
[CI 34746909758](https://github.com/Rapto0/Rapot/actions/runs/34746909758) and
[image publication 34747132287](https://github.com/Rapto0/Rapot/actions/runs/34747132287).
The bounded frontend production rollout passed on 13 September at 08:59:10 UTC.
This completed the first COMBO fix. The remaining P3-1 work was accepted in the
later source and 21 September Pine closure records below.

For this P3-1 first step, the component rollout avoided another full source archive
after the exact Git diff was restricted to reviewed frontend files and documentation,
with build/dependency inputs, backend code, schemas and Compose unchanged. Retain
the current `279aa9fea99b520e661b43f104a2bf4791893ac3` Compose source,
`/opt/rapot/current`, `RAPOT_RELEASE` and all backend image selections. Record the
frontend revision separately in a canonical component manifest: base/new source
SHAs, reviewed paths and Git file hashes, exact successful CI/publication runs,
and the immutable frontend image digest with matching OCI source identity.
Verify these against the deployed base and candidate image before cutover; do not
describe the mixed component revisions as a whole-stack source upgrade.

Measure pending compressed layers, unpacked allocations and metadata against
fresh disk capacity before each pull; retain the **400 MiB reserve + 128 MiB growth
allowance** without weakening either. Keep the previous frontend image and exact
selection for rollback. Replace only the frontend digest in the image override,
verify resolved Compose differs only there, and start only `frontend` with
`up -d --no-deps --no-build --pull never` using the retained Compose source.
This path runs no DB initializer, migration or backup restore and does not restart
API, bot, middleware or PostgreSQL. Their container IDs, images, start times and
restart counts, plus credential/release environment and Nginx hashes, must remain
unchanged. Preserve every existing backup and rollback image; the component
manifest alternative does not authorize pruning or a paid capacity increase.

Accept the exact frontend image through HTTPS/SSR, assets and the relevant
COMBO/worker/local-alarm checks, then verify protected services and configuration
again. On failure, restore only the previous frontend selection and verify it is
healthy. Record source/image identity, checks, capacity and result in versioned
operator evidence. No actual alarm delivery, exchange order or full P3-1 completion
is implied by this frontend acceptance.

The published frontend digest is
`sha256:9b9fd4dda8a62adb568dbce71b5eda8111c2c583d6130de6db07efa280512f3b`.
Its first 11 layers are shared; the remaining two require **19,369,458 B** compressed,
**65,929,216 B** conservative unpacked allocation and **13,140 B** metadata.
With the fixed reserves and 2 MiB evidence budget, free space must exceed
**641,057,094 B**. The predeployment observation was **578,150,400 B**: roughly
60 MiB more was needed at that time. Those measurements and the initial no-pull
state are historical; the approved cleanup and actual rollout follow below.

The one-file predeployment proposal identified an unused, backed-up ARCHIVED system
journal with **75,501,568 B** allocated.
The exact path/hash and private archive verification are in the continuation plan
and `runtime-data/p31-one-journal-removal-proposal.json`, SHA256
`9f88d6e7c18307c3dcd080ecedd9b4f6c38a1c3fb299b60255f2a1b0ddf64e65`.
The earlier four-file approval did not cover this proposal. The user subsequently
answered the exact one-file question with a direct continuation instruction; that
new scoped approval and fresh backup/file/use/runtime checks were recorded before
removal. Only that journal was removed at 08:52:55 UTC; the other seven archived
journals and private backup were retained. That approval authorized no further deletion.
Preparation commit `5c7c47c`, successful CI `34747715788`, and canonical blob hashes
were recorded under
`/root/rapot-ops/20260913-p31-preflight/release-record.json`; that record is not
a successful deployment. The component rollout uses a separate
`/root/rapot-ops/20260913-p31-frontend/` operation record.

The actual rollout receipt is `deployment.json` in that component operator directory.
It records frontend `967f137` and backend/Compose/current `279aa9f` separately.
Only the frontend image override changed; four protected containers and fixed
environment/Nginx hashes stayed identical. Eight health/SSR GETs passed. Final
free space was **562,618,368 B**, above the unchanged 528 MiB reserve.
The canonical source/capacity proofs were hardlinked from the private preflight
directory; only the **34,902 B** pinned operator was uploaded again. These two
proof files are immutable and must not be edited through either link.

The exact cleanup receipt is `one-journal-removal-result.json` in the preflight
directory. External HTTPS chart/RSC/static-file delivery is recorded separately
in `p31-frontend-public-acceptance.json`: 16 GETs passed at 09:01:55 UTC, including
chart/alarms HTML, ETHUSDT/Kripto RSC props, and 12 JS + 1 CSS files sampled from
the discovered 15 JS + 1 CSS inventory (868,343 B total). It does not assert browser
worker execution
or an exchange/TradingView acceptance test. Final three-document Git SHA/CI, blob
hashes and publication checks belong in the component directory
`documentation-release-record.json`. Documentation publication performs no
application restart, image build, migration or further deletion.

## P1-G2 dependency component rollout — 20 September 2026

The reviewed P1-G2 exception changes frontend package/lock inputs, the audit script
and tests, CI audit configuration and documentation. Its canonical source proof
binds exactly 11 allowed paths against `d79f4cc`, plus the unchanged inherited
frontend test fixture. It keeps backend code, schemas, Dockerfiles, Compose and
the image publication workflow unchanged. This exception does not relax the earlier
P2-1/P3-1 source scopes or authorize an arbitrary dependency rollout.

Source `bbd9377cfd3e8b74f6b02ba23c1c99282ba587bd` passed
[CI 34757348090](https://github.com/Rapto0/Rapot/actions/runs/34757348090) and
[image publication 34757661535](https://github.com/Rapto0/Rapot/actions/runs/34757661535).
The frontend-only operator completed at **08:10:01 UTC**, using digest
`sha256:e312d7aa5e682a7835e4dc7ba3e1b4263f04a64f872f47037814ec4b0ba1f4d0`.
Frontend now records `bbd9377`; backend, Compose, current and `RAPOT_RELEASE`
remain `279aa9f`. Only the frontend image override changed. Four protected container
identities/start times/restart counts and fixed environment/Nginx bytes matched;
the new frontend had zero restarts and all eight health/SSR GETs passed.

Staging uploaded three pinned files into `/root/rapot-ops/20260920-p1g2-frontend/`;
it used no hardlinks. Exact successful workflows, authorized cleanup evidence and
the five-container/config/current snapshot were checked before the first write.
The strict pre-staging requirement was **F > 661,207,283 B**, including one total
2 MiB input/config/evidence allowance and the unchanged 528 MiB reserve. Subsequent
gates debited only actual allocated OPS blocks from that same allowance. Fresh
private configuration copies and the old frontend image were retained for rollback.
No database initializer, migration, restore or backend lifecycle command ran.

The user approved three named archived journals. Two were already absent before
cleanup, for an unverified reason; only the remaining authorized, freshly verified
copy was removed. The private backup remains. Observed free space was
**702,586,880 B** after cleanup and **603,271,168 B** at deploy acceptance. These
are checkpoint measurements. The exact paths, authorization and preservation
checks are in the [continuation plan](RAPOT_DEVAM_PLANI.md).

External public v2 acceptance passed **16 GETs at 08:11:44 UTC**, covering chart/
alarms HTML, ETHUSDT/Kripto RSC props and 12 JS + 1 CSS sampled from 14 JS + 1 CSS;
**948,746 B** were read. The original request stopped at Next's 307 RSC query guard.
The v2 probe supplied the required empty `_rsc` parameter on its fixed navigation
URL and retained redirect refusal. The failed original record remains separate.
This verifies delivery, not browser workers, COMBO arithmetic or alarm execution.

Native v2 acceptance completed at **08:17:07 UTC**, bound to the actual frontend
container, immutable image and source. Linux/x64/musl reported Node **20.20.2**,
Next **16.3.5**, Sharp **0.35.4**, heif metadata **1.23.2** and native libvips
**8.18.6**; Sharp selected the verified native binding, with no global or WASM
fallback. The original probe produced no output because its stdin entry condition
did not run; that failure was preserved and the helper was corrected. The v2
metadata probe decoded no image and made no application mutation. Final runtime
verification retained all expected identities/configuration and **602,435,584 B**
free space, above the fixed reserve. See the separate native/public/final `-v2`
records for these checks; the deploy receipt alone is not their substitute.

The deployment receipt is `deployment.json` in the component OPS directory,
SHA256 `a676adc4549f26819e83874cd679bf9dacbdc04179e442ad9eca8a663f002701`.
Public/native metadata checks and their limits are recorded separately in the
[frontend security review](FRONTEND_DEPENDENCY_SECURITY.md) and continuation
plan. Final document commit/CI, canonical blob hashes and publication checks belong
under `/root/rapot-ops/20260920-p1g2-closure/release-record.json`; the existence of
the deploy receipt does not imply that closure documents have already been published.
DRY_RUN/trading=false/live=false, disabled AI, all databases and rollback resources
remain preserved; no paid upgrade or exchange/TradingView acceptance is implied.

## P3-1 shared portfolio source publication — 20 September 2026

The fifth backtest step changes the separate `backtesting_system.py` CLI and its
synthetic tests/documents. It orders one market's shared cash by day and symbol,
then records all open positions at their last observed closing prices. Missing
calendar days retain explicit mark dates and stale-symbol metadata. It does not
change the scanner, API, frontend, Pine or exchange execution path.

After exact-source CI succeeds, publish the eight reviewed canonical Git files
and the bounded local acceptance record under
`/root/rapot-ops/20260920-p31-portfolio/`. Its `release-record.json` records the
full source/CI identity, Git blob hashes, transferred bytes and before/after
runtime/configuration and HTTPS checks. Require the unchanged 528 MiB reserve
plus a total 2 MiB publication allowance before the first write.

This is an operator source copy. It neither updates the CLI inside existing
containers nor runs it. Production remains frontend `bbd9377`, backend/Compose/
current `279aa9f`; no image pull, service restart, initializer, migration, database
restore or deletion is part of this publication. Actual provider, full CLI/chart,
benchmark/WFA, TradingView and exchange acceptance remain separate. The
[portfolio contract](BACKTEST_PORTFOLIO.md) describes the tested behavior.

## P3-1 final backtest source acceptance — 20 September 2026

The final code step fixes NAV benchmark comparisons, names the window analysis
as rolling buy-and-hold, and adds the isolated full fixture CLI with actual
JSON/CSV/SVG/XLSX reports. Production services do not import this separate CLI.

Publish the 15 canonical source/test/document files, nine verified fixture
artifacts and two small acceptance/measurement manifests only after successful
exact-source CI. The destination is `/root/rapot-ops/20260920-p31-final/`; its
`release-record.json` binds the source commit, CI, canonical hashes, fixture
files, unchanged runtime and fresh HTTPS/capacity checks. The full strategy
measurement stays local/CI; its hash and source/lock identity are bound by the
compact manifest. Require the fixed 528 MiB reserve plus the 2 MiB publication
budget before the first write; no service change, deletion or database action
is included. Frontend `bbd9377`, backend/Compose/current `279aa9f` remain active.

The code and offline acceptance do not certify TradingView compilation/runtime.
On 20 September no browser was connected. Separate current-source acceptance
was completed on 21 September as recorded below; the earlier user reports and
narrow Pine source tests were not used as substitutes.
Deferred real alarm/testnet/order acceptance remains outside this publication.

## P3-1 Pine and P3-2 decision closure — 21 September 2026

The unchanged 1,091-line Pine source was copied into TradingView, checked by
SHA256 before paste, after editor copyback and after reopening the saved private
script. On BINANCE:BTCUSDT / standard Candles / 1D it compiled and rendered the
score table and TF OK status. See [Pine acceptance](PINE_RUNTIME_ACCEPTANCE.md).
No alert was created or changed and no exchange order was sent. P3-2 reviewed
the five backup commits and selected no code/document transplant; its
[decision](BACKUP_BRANCH_REVIEW.md) preserves main and the backup ref.

After exact successful CI, publish only six canonical documents (`AGENTS.md`,
the continuation plan, strategy comparison, this deployment guide, and the two
acceptance/decision documents) plus the small Pine acceptance JSON into
`/root/rapot-ops/20260921-p31-p32-closure/`. Its `release-record.json` records
the exact commit, CI, blob hashes, fresh health/capacity checks and stable
production identity, chained to the 20 September final source receipt.
The local copy is `runtime-data/p31-p32-closure-release-record.json`.
Require the fixed 528 MiB reserve plus 2 MiB publication budget before the first
write; use exclusive versioned files and verify readback hashes. This does not
pull images, restart services, change config/current pointers or touch databases.
Frontend `bbd9377` and backend/Compose/current `279aa9f` remain in place.

## Optional middleware

Create `middleware/.env` or select `RAPOT_MIDDLEWARE_ENV_FILE`, outside Git:

```dotenv
POSTGRES_PASSWORD=<strong-password>
MW_DATABASE_URL=postgresql+psycopg://rapot_middleware:<URL-encoded-password>@postgres:5432/rapot_middleware
MW_WEBHOOK_AUTH_TOKEN=<webhook-credential>
MW_ADMIN_AUTH_TOKEN=<different-management-credential>
MW_INVENTORY_ACCOUNT_ID=production-simulation
```

The password must match in both entries; URL-encode it in `MW_DATABASE_URL`. PostgreSQL
user/database are `rapot_middleware`. No real broker key is needed for the disabled rollout.
Use `config --quiet`, since ordinary Compose config output can expose environment secrets.

```bash
docker compose --profile middleware config --quiet
docker compose --profile middleware build middleware
docker compose --profile middleware up -d --wait --wait-timeout 180 middleware
docker compose --profile middleware logs --tail 100 middleware-migrate middleware
curl --fail http://127.0.0.1:8001/health
```

Alembic head is currently `20260907_0006`. Production refuses missing/old revisions.
Existing unversioned `mw_*` tables are never automatically stamped: back up and verify their
actual schema before an explicit baseline. Historical scope/commission classification rules
in [the middleware guide](MIDDLEWARE.md) remain applicable. Main SQLite uses its separate migration policy.

Stop with `docker compose stop` (include `--profile middleware` for that profile). Do not
use `down -v` during upgrades: it deletes DB volumes. Rollback needs reviewed code/schema
compatibility; never automatically downgrade live data.

## CI and publication

`ci.yml` checks Python/frontend and builds both images. It verifies backend imports without
network access, migrates a disposable PostgreSQL database to Alembic head, starts middleware
with production schema checks and trading disabled, and serves frontend HTML/static assets
from the built container. The separate standalone proxy test uses local mock API/health
servers, including a WebSocket upgrade.

P2-3 enables Ruff lint/format for all tracked Python sources. Security artifacts contain
Bandit source findings and pip-audit results for the exact active Python lock pins.
Findings are explicitly report-only while triage is open; tool failures, incomplete scope
and invalid reports fail CI. A successful workflow is not evidence of zero vulnerabilities.
Check the security summary/artifact as well as the exact source SHA and workflow result.

P2-3 changes UTC timestamp construction without changing the existing naive-UTC storage
contract or database schema. It requires no manual migration/backfill. The rollout still
requires a fresh verified backup. On the current space-constrained host, a bounded logical
SQL gzip snapshot may be used only after an independent restore verifies integrity, schema,
metadata and typed row-content fingerprints from the same source read transaction.
Transport hashes and row counts alone do not establish a restorable backup. Existing data,
archives and rollback images must be preserved; failed preparation does not permit rollout.

These checks do not validate existing VPS data, the complete Compose network, production
volume permissions, reverse proxy/TLS, or actual broker operations. Complete the cutover
checks above on the authorized server before declaring deployment successful.
`deploy.yml` publishes backend/frontend images with full source SHA tags on release/manual
invocation. It has no server deploy job. Compose above builds locally from the verified
checkout; publishing images does not update the VPS.
