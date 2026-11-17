import asyncio
import json
import multiprocessing as mp
import os
from dataclasses import asdict
from multiprocessing.connection import Connection
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.middleware.base import RequestResponseEndpoint

from app.config import LIMITS
from app.models import Options, ServiceError
from app.exports import generate_exports
from app.pdf import render_pdf
from app.security import receive
from app.service import build, require_ready
from app.selection import matches_identity

app = FastAPI(title="Procontel · Boletas", docs_url=None, redoc_url=None, openapi_url=None)
slots = asyncio.Semaphore(LIMITS.concurrency)
NO_STORE = {
    "Cache-Control": "no-store, private",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


def worker(connection: Connection, data: bytes, options_json: str, action: str) -> None:
    """One disposable process per request: timeout terminates actual CPU work."""
    try:
        options = Options.model_validate_json(options_json)
        result, records, issues = build(data, options)
        if action in {"analyze", "review"}:
            connection.send((200, result, "application/json", None))
            return
        require_ready(issues)
        if action == "preview":
            identity = options.preview_record
            selected = [r for r in records if identity and matches_identity(r, identity)]
            if len(selected) != 1:
                raise ServiceError(
                    422, "INVALID_PREVIEW", "Selecciona una persona válida para la vista previa."
                )
            connection.send(
                (
                    200,
                    render_pdf(selected, result["company"], options),
                    "application/pdf",
                    "preview.pdf",
                )
            )
            return
        payload, media, filename = generate_exports(data, records, result["company"], options)
        connection.send((200, payload, media, filename))
    except (ValidationError, json.JSONDecodeError):
        connection.send(
            (
                400,
                {
                    "code": "INVALID_OPTIONS",
                    "message": "Opciones inválidas: revisa campos, formatos y confirmaciones.",
                    "issues": [],
                },
                "application/json",
                None,
            )
        )
    except ServiceError as exc:
        connection.send(
            (
                exc.status,
                {
                    "code": exc.code,
                    "message": exc.message,
                    "issues": [asdict(i) for i in exc.issues],
                },
                "application/json",
                None,
            )
        )
    except Exception:
        connection.send(
            (
                500,
                {
                    "code": "INTERNAL_ERROR",
                    "message": "No se pudo completar la solicitud.",
                    "issues": [],
                },
                "application/json",
                None,
            )
        )
    finally:
        connection.close()


@app.middleware("http")
async def privacy_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    response = await call_next(request)
    response.headers.update(NO_STORE)
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'self'"
    return response


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def process(request: Request, action: str) -> Response:
    request_id = uuid4().hex
    origin = request.headers.get("origin")
    expected_origin = os.getenv("PUBLIC_ORIGIN") or str(request.base_url).rstrip("/")
    if (origin and origin != expected_origin) or request.headers.get(
        "sec-fetch-site"
    ) == "cross-site":
        return JSONResponse(
            {
                "code": "ORIGIN_REJECTED",
                "message": "Se requiere el mismo origen.",
                "issues": [],
                "request_id": request_id,
            },
            status_code=403,
        )
    if slots.locked():
        return JSONResponse(
            {
                "code": "CAPACITY_EXCEEDED",
                "message": "Capacidad ocupada; inténtalo de nuevo.",
                "issues": [],
                "request_id": request_id,
            },
            status_code=429,
        )
    async with slots:
        parent = child = task_process = None
        try:
            async with asyncio.timeout(LIMITS.timeout):
                data, options = await receive(request)
                ctx = mp.get_context("spawn")
                parent, child = ctx.Pipe(duplex=False)
                task_process = ctx.Process(
                    target=worker, args=(child, data, options, action), daemon=True
                )
                task_process.start()
                child.close()
                del data
                while not parent.poll():
                    if await request.is_disconnected():
                        raise ServiceError(499, "CANCELLED", "Solicitud cancelada.")
                    if not task_process.is_alive():
                        raise ServiceError(
                            500, "WORKER_FAILED", "No se pudo completar la solicitud."
                        )
                    await asyncio.sleep(0.025)
                status, payload, media, filename = await asyncio.to_thread(parent.recv)
                if media == "application/json":
                    if status != 200:
                        payload["request_id"] = request_id
                    return JSONResponse(payload, status_code=status)
                disposition = "inline" if action == "preview" else "attachment"
                return Response(
                    payload,
                    media_type=media,
                    headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
                )
        except TimeoutError:
            return JSONResponse(
                {
                    "code": "PROCESS_TIMEOUT",
                    "message": "Se excedió el tiempo de procesamiento.",
                    "issues": [],
                    "request_id": request_id,
                },
                status_code=504,
            )
        except ServiceError as exc:
            return JSONResponse(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "issues": [asdict(i) for i in exc.issues],
                    "request_id": request_id,
                },
                status_code=exc.status,
            )
        except Exception:
            return JSONResponse(
                {
                    "code": "INTERNAL_ERROR",
                    "message": "No se pudo completar la solicitud.",
                    "issues": [],
                    "request_id": request_id,
                },
                status_code=500,
            )
        finally:
            if task_process is not None:
                if task_process.is_alive():
                    task_process.terminate()
                await asyncio.to_thread(task_process.join, 2)
                if task_process.is_alive():
                    task_process.kill()
                    await asyncio.to_thread(task_process.join)
                task_process.close()
            for connection in (parent, child):
                if connection:
                    connection.close()


@app.post("/api/v1/analyze")
async def analyze(request: Request) -> Response:
    return await process(request, "analyze")


@app.post("/api/v1/review")
async def review(request: Request) -> Response:
    return await process(request, "review")


@app.post("/api/v1/preview")
async def preview(request: Request) -> Response:
    return await process(request, "preview")


@app.post("/api/v1/generate")
async def generate(request: Request) -> Response:
    return await process(request, "generate")
