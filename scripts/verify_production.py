"""Read-only deployment smoke test using TLS validation and interactive credentials."""

import base64
import getpass
import os
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main() -> None:
    origin = os.environ.get("PUBLIC_ORIGIN", "").rstrip("/")
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit(
            "Configura PUBLIC_ORIGIN con el origen HTTPS de producción, sin ruta."
        )
    opener = build_opener(NoRedirect())

    def check(path, expected, authorization=None, method="GET", extra_headers=None):
        headers = dict(extra_headers or {})
        if authorization:
            headers["Authorization"] = authorization
        request = Request(origin + path, headers=headers, method=method)
        try:
            response = opener.open(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, (
                f"{path}: HTTP {response.status}, esperado {expected}"
            )
            assert response.headers.get("X-Content-Type-Options") == "nosniff", path
            assert response.headers.get("Content-Security-Policy"), path
            if path == "/" or path.startswith("/api/"):
                assert "no-store" in response.headers.get("Cache-Control", ""), path
            if expected == 401:
                assert response.headers.get("WWW-Authenticate", "").startswith(
                    "Basic"
                ), path
        print(f"OK: {method} {path} → {expected}")

    for path in ("/", "/api/v1/analyze", "/api/v1/generate"):
        check(path, 401, method="POST" if path.startswith("/api/") else "GET")
    username = input("Usuario autorizado: ").strip()
    password = getpass.getpass("Contraseña: ")
    authorization = (
        "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()
    )
    check("/", 200, authorization)
    check("/api/v1/analyze", 400, authorization, "POST")
    check(
        "/api/v1/analyze",
        403,
        authorization,
        "POST",
        {"Origin": "https://untrusted.invalid"},
    )
    print(
        "Prueba básica completada. Falta verificar la carga y descarga con una planilla sintética."
    )


if __name__ == "__main__":
    main()
