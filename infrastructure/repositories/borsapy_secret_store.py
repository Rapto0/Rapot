"""Authenticated encryption for write-only integration credentials."""

import base64
import json
import os
import stat
import tempfile
from pathlib import Path


class SecretStoreError(Exception):
    """Credential storage could not be used safely."""


class BorsapySecretStore:
    """Keep ciphertext separate from the existing server signing secret."""

    def __init__(self, path: Path, secret: str):
        self.path = path
        self._secret = secret

    def _cipher(self):
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF

        if len(self._secret) < 32:
            raise SecretStoreError("Kimlik saklama için en az 32 karakter JWT anahtarı gerekiyor.")
        key = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=b"rapot/borsapy/secrets/v1"
        ).derive(self._secret.encode())
        return Fernet(base64.urlsafe_b64encode(key))

    def _check(self) -> None:
        if self.path.is_symlink() or any(parent.is_symlink() for parent in self.path.parents):
            raise SecretStoreError("Kimlik dosyası yolu güvenli değil.")
        if self.path.exists():
            mode = self.path.stat().st_mode
            if not stat.S_ISREG(mode) or self.path.stat().st_size > 65536:
                raise SecretStoreError("Kimlik dosyası geçersiz.")
            if os.name != "nt" and stat.S_IMODE(mode) & 0o077:
                raise SecretStoreError("Kimlik dosyası izinleri 0600 olmalı.")

    def load(self) -> dict[str, str]:
        try:
            self._check()
            if not self.path.exists():
                return {}
            data = json.loads(self._cipher().decrypt(self.path.read_bytes()))
            if not isinstance(data, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in data.items()
            ):
                raise ValueError
            return data
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError(
                "Kimlik dosyası çözülemedi; bağlantıyı yeniden kaydedin."
            ) from None

    def revision(self) -> tuple[int, int, int, int] | None:
        """Detect atomic replacement/deletion without decrypting or returning any data."""
        try:
            self._check()
            if not self.path.exists():
                return None
            info = self.path.stat()
            return (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError("Kimlik dosyası durumu okunamadı.") from None

    def save(self, values: dict[str, str]) -> None:
        temporary = None
        try:
            self._check()
            payload = self._cipher().encrypt(json.dumps(values).encode())
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if os.name != "nt" and stat.S_IMODE(self.path.parent.stat().st_mode) & 0o077:
                raise SecretStoreError("Kimlik dizini izinleri 0700 olmalı.")
            descriptor, temporary = tempfile.mkstemp(prefix=".credentials-", dir=self.path.parent)
            with os.fdopen(descriptor, "wb") as file:
                file.write(payload)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
            temporary = None
            if os.name != "nt":
                directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError("Kimlik dosyası kaydedilemedi.") from None
        finally:
            if temporary:
                Path(temporary).unlink(missing_ok=True)

    def clear(self) -> None:
        try:
            self._check()
            self.path.unlink(missing_ok=True)
        except SecretStoreError:
            raise
        except Exception:
            raise SecretStoreError("Kimlik dosyası silinemedi.") from None
