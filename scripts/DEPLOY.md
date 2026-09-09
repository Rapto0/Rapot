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

The recorded target is `root@138.68.71.27`, `/root/Rapot`. The September 2026 local SSH
attempt failed authentication; no usable private key was found on the development computer.
No VPS deployment has been verified in P1-2. Use an authorized server console or arrange
SSH access through the server owner; never paste private keys or passwords into reports.

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

Frontend image builds use `API_PROXY_TARGET=http://api:8000` and
`HEALTH_PROXY_TARGET=http://bot:5000`; changing these targets requires a rebuild. Browser HTTP
and WebSockets use `/api`, health uses `/health-api`. Local npm builds default to localhost
8000/5000. These defaults must not be confused with container-local localhost.

## Release

Complete tests, lint/types, builds and required CI for the exact commit. The first release
still requires P1-7 and P1-2 verification. `scripts/deploy.ps1` checks clean tree/branch/full
SHA, optionally pushes, then prints server commands. It does not stage, commit, stash, reset
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

`ci.yml` checks Python/frontend and builds both images, including isolated backend imports.
`deploy.yml` publishes backend/frontend images with full source SHA tags on release/manual
invocation. It has no server deploy job. Compose above builds locally from the verified
checkout; publishing images does not update the VPS.
