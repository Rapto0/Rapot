"""
Shared SSL helpers for Is Yatirim endpoints.
"""

from __future__ import annotations

import os
import ssl
import tempfile
from pathlib import Path

from logger import get_logger

logger = get_logger(__name__)

_isyatirim_ca_bundle_ready = False

ISYATIRIM_INTERMEDIATE_PEM = """-----BEGIN CERTIFICATE-----
MIIElzCCA3+gAwIBAgIRAIPahmyfUtUakxi40OfAMWkwDQYJKoZIhvcNAQELBQAw
TDEgMB4GA1UECxMXR2xvYmFsU2lnbiBSb290IENBIC0gUjMxEzARBgNVBAoTCkds
b2JhbFNpZ24xEzARBgNVBAMTCkdsb2JhbFNpZ24wHhcNMjUwNzE2MDMwNTQ2WhcN
MjcwNzE2MDAwMDAwWjBTMQswCQYDVQQGEwJCRTEZMBcGA1UEChMQR2xvYmFsU2ln
biBudi1zYTEpMCcGA1UEAxMgR2xvYmFsU2lnbiBHQ0MgUjMgRVYgVExTIENBIDIw
MjUwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDEG4l4CpUk556CyXIA
B3ihV2b8sWMNGwnW0wCpuaHHA5rlXpSWE1AD6r9hyGhQOrc45nPOj6Fvsqw8dFZw
FpAJzlk6FxhYP1ve8KPJvIpt6f5v28jOlzfs8c7dJ8ZmqKHB0Zj6RbAvA9vAl2A3
j0mu+ooXN3/QaFvVihDV/SRyOfFBlhPAsRk8y97tLPWx7/4YzfE6NSLKsU1yF+tf
BTttbaXTH/cWY/KQE3ZHTFRo6XouemjPBP9CDXeTR11tm37Bgn3QOj93FHdi1JJp
eNBGEOGvM8qhTV/77kDiUyOvsp4jZOhas6kIRn8nWK7fCPNdFJYi1Ctvd7gnQ1gB
lW71AgMBAAGjggFrMIIBZzAOBgNVHQ8BAf8EBAMCAYYwHQYDVR0lBBYwFAYIKwYB
BQUHAwEGCCsGAQUFBwMCMBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0OBBYEFGMQ
f+QoM5r4R2BZUn5XEMdN+BcWMB8GA1UdIwQYMBaAFI/wS3+oLkUkrk1Q+mOai97i
3Ru8MHsGCCsGAQUFBwEBBG8wbTAuBggrBgEFBQcwAYYiaHR0cDovL29jc3AyLmds
b2JhbHNpZ24uY29tL3Jvb3RyMzA7BggrBgEFBQcwAoYvaHR0cDovL3NlY3VyZS5n
bG9iYWxzaWduLmNvbS9jYWNlcnQvcm9vdC1yMy5jcnQwNgYDVR0fBC8wLTAroCmg
J4YlaHR0cDovL2NybC5nbG9iYWxzaWduLmNvbS9yb290LXIzLmNybDAtBgNVHSAE
JjAkMAcGBWeBDAEBMAwGCisGAQQBoDIKAQEwCwYJKwYBBAGgMgEBMA0GCSqGSIb3
DQEBCwUAA4IBAQCtcTjIgw+tiW7E+sCTJ36nrC0IOxMpwE+nTaUG1xQJb+QE18vF
cPvEiqv8OonEBkQJFQ1N5YdDu9kydDYXBmIheYD9Z//TlUBnLL7HBje1ugplB0xE
jpU52q0XLxe6nHfeEKnslZ/Q/eDEsjZKxwF51SlGO6ap+09hfdbfMXDkTsfa+yXg
dIxZRCud0QEBTZAow0iCs3rf5wVALhhh2ePEwqxEm1LkUhvkJMLSCobYcJ+vXprK
JijbpPM602H1kqxNcD/nE7aCNm7g5GTaT04SCGYiQJ32r9mhx34peuYz05pY+AA3
aVB22PDvfoNyGZyClRtNt4KKg8dGJlYEhc3D
-----END CERTIFICATE-----"""


def ensure_isyatirim_ca_bundle() -> Path | None:
    """
    Merge certifi CA bundle with the missing Is Yatirim intermediate certificate.
    Returns the merged bundle path on success.
    """
    global _isyatirim_ca_bundle_ready

    try:
        import certifi

        base_bundle = Path(certifi.where())
        merged_bundle = Path(tempfile.gettempdir()) / "rapot_requests_ca_bundle_isyatirim.pem"

        base_data = base_bundle.read_bytes()
        intermediate_data = ISYATIRIM_INTERMEDIATE_PEM.encode("ascii")
        if intermediate_data not in base_data:
            merged_bundle.write_bytes(base_data.rstrip() + b"\n" + intermediate_data + b"\n")
        else:
            merged_bundle.write_bytes(base_data)

        os.environ["REQUESTS_CA_BUNDLE"] = str(merged_bundle)
        os.environ["SSL_CERT_FILE"] = str(merged_bundle)
        _isyatirim_ca_bundle_ready = True
        return merged_bundle
    except Exception as exc:
        logger.warning(f"Is Yatirim CA bundle hazirlanamadi: {exc}")
        return None


def get_isyatirim_ssl_context() -> ssl.SSLContext | None:
    bundle_path = ensure_isyatirim_ca_bundle()
    if bundle_path is None:
        return None

    try:
        return ssl.create_default_context(cafile=str(bundle_path))
    except Exception as exc:
        logger.warning(f"Is Yatirim SSL context olusturulamadi: {exc}")
        return None
