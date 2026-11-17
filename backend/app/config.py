import os
from dataclasses import dataclass
from urllib.parse import urlsplit


def validate_production_origin() -> None:
    if os.getenv("APP_ENV") != "production":
        return
    origin = os.getenv("PUBLIC_ORIGIN", "")
    try:
        parsed = urlsplit(origin)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
        if (
            parsed.scheme == "https"
            and parsed.hostname
            and not parsed.username
            and not parsed.password
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and valid_port
        ):
            return
    except ValueError:
        pass
    raise RuntimeError(
        "Producción requiere PUBLIC_ORIGIN con origen HTTPS sin ruta ni credenciales."
    )


validate_production_origin()


@dataclass(frozen=True)
class Limits:
    upload: int = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
    expanded: int = int(os.getenv("MAX_EXPANDED_BYTES", 100 * 1024 * 1024))
    entries: int = 2000
    xml: int = 16 * 1024 * 1024
    rows: int = 1200
    cells: int = 100_000
    people: int = 1000
    concurrency: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    timeout: int = int(os.getenv("PROCESS_TIMEOUT_SECONDS", "60"))


LIMITS = Limits()
SCHEMA = "procontel_fixed_v1"
