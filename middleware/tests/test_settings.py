from __future__ import annotations

import pytest

from middleware.infra.settings import settings


def test_runtime_config_rejects_disabled_webhook_auth_in_production():
    settings.app_env = "production"
    settings.require_webhook_auth = False

    with pytest.raises(ValueError, match="MW_REQUIRE_WEBHOOK_AUTH"):
        settings.validate_runtime_configuration()
