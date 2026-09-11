# Verified commit → Docker Compose

Supported production topology: Compose 2.24+, Python 3.12.8 with runtime dependencies
constrained by `requirements-dev.lock`, Node 20.20.2/npm 10.9.9 and Next.js standalone.
PM2 files are explicit legacy launchers; they are not a second production supervisor.

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
see [the current release and evidence record](../docs/RAPOT_DEVAM_PLANI.md). Keep private
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

For a change confined to frontend application code and release documentation, verify the
exact source diff first. Backend code, Compose, lock files and build inputs must be unchanged.
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
in `middleware/README.md` remain applicable. Main SQLite uses its separate migration policy.

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
