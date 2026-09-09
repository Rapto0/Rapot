"""Canonical container entry points. Invoke from the repository root."""

from __future__ import annotations

import argparse
import os
import runpy
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "service", choices=("init-main-db", "api", "bot", "migrate-middleware", "middleware")
    )
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error("Supported deployment runtime is Python 3.12")

    if args.service.startswith("middleware") or args.service == "migrate-middleware":
        if not os.environ.get("MW_DATABASE_URL", "").strip():
            parser.error("Set MW_DATABASE_URL explicitly for the dedicated middleware database")
        from middleware.infra.db import get_engine
        from middleware.infra.schema import migrate_schema, require_current_schema
        from middleware.infra.settings import settings as middleware_settings

        middleware_settings.validate_runtime_configuration()
        if args.service == "migrate-middleware":
            migrate_schema(get_engine())
            return
        require_current_schema(get_engine())
        import uvicorn

        uvicorn.run("middleware.api.main:app", host="0.0.0.0", port=8001, workers=1)
    elif args.service == "init-main-db":
        from db_session import init_db

        init_db()
    elif args.service == "api":
        # Apply before settings or the API module is imported.
        os.environ["RUN_EMBEDDED_BOT"] = "false"
        import uvicorn

        uvicorn.run("api.main:app", host="0.0.0.0", port=8000, workers=1)
    else:
        runpy.run_module("main", run_name="__main__")


if __name__ == "__main__":
    main()
