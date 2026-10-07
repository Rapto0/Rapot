"""Volume provenance shared by private chart/research presentation boundaries."""

import math
from typing import Any


def native_volume(value: Any) -> float | None:
    """Keep genuine zero; missing, negative and provider sentinel values are unknown."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) and 0 <= number < 1e99 else None


def volume_quality(verified: bool, unavailable_rows: int | None = None) -> dict:
    state = "verified" if verified else "unavailable" if unavailable_rows else "unverified"
    return {
        "state": state,
        "verified": verified,
        "unavailable_rows": 0 if verified else unavailable_rows,
        "message": "Hacim sağlayıcının mum verisinde doğrulandı."
        if verified
        else "Sağlayıcı bu mumlarda kullanılabilir hacim göndermedi; sıfır hacim değildir."
        if state == "unavailable"
        else "Bu serinin hacmi doğrulanamadı; hacme bağlı hesaplar kullanılamaz.",
    }


def frame_volume_quality(frame: Any) -> dict:
    """A numeric placeholder, including zero, is not native-field provenance."""
    verified = (
        frame.attrs.get("volume_verified") is True
        and len(frame) > 0
        and "Volume" in frame
        and all(native_volume(value) is not None for value in frame.Volume.tolist())
    )
    count = frame.attrs.get("volume_unavailable_rows")
    if type(count) is not int or not 0 <= count <= len(frame):
        count = None
    return volume_quality(verified, count)
