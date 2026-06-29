"""FastAPI app factory for the SakaiBot control panel.

Thin layer: each route delegates to a service method and returns its dict.
No business logic here. Static SPA is served unauthenticated (it's just the
shell); every ``/api/*`` route except ``/api/health`` requires the token.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ..utils.logging import get_logger
from .auth import require_token
from .avatars import initials_svg
from .errors import PanelError, PanelNotFound

logger = get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def _attachment_disposition(name: str) -> str:
    """Header-injection-safe ``Content-Disposition: attachment`` for a download.

    Quotes/newlines/non-ASCII in a Telegram-supplied filename can't break the
    header: the ASCII fallback keeps only safe chars, and ``filename*`` carries
    the real (percent-encoded UTF-8) name for clients that honor RFC 5987."""
    from urllib.parse import quote

    ascii_name = "".join(
        c if (c.isalnum() or c in "._- ") else "_" for c in name
    )[:120] or "download"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"


def create_app(state: Any) -> FastAPI:
    app = FastAPI(title="SakaiBot Control Panel", docs_url=None, redoc_url=None)
    app.state.panel = state

    # ---- error handlers (never leak internals) ----
    @app.exception_handler(PanelError)
    async def _panel_error(_: Request, exc: PanelError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled panel error: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content={"ok": False, "error": "Internal panel error."})

    # ---- open health route ----
    @app.get("/api/health")
    async def health() -> Dict[str, Any]:
        return {
            "ok": True,
            "panel": "up",
            "client": "connected" if state.client_ready() else "degraded",
        }

    api = APIRouter(prefix="/api", dependencies=[Depends(require_token)])

    # ---- dashboards ----
    @api.get("/status")
    async def status() -> Dict[str, Any]:
        return await state.status.account()

    @api.get("/keys")
    async def keys() -> Dict[str, Any]:
        return state.keys.list_keys()

    @api.post("/keys")
    async def keys_add(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.keys.add_key(payload.get("provider"), payload.get("key", ""))

    @api.put("/keys/provider")
    async def keys_provider(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.keys.set_provider(payload.get("primary"), payload.get("fallback"))

    @api.put("/keys/models")
    async def keys_models(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.keys.set_models(payload.get("overrides", {}))

    @api.post("/keys/test")
    async def keys_test(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.keys.test_key(
            payload.get("provider"), key=payload.get("key"), index=payload.get("index")
        )

    @api.put("/keys/{provider}/{index}")
    async def keys_set(provider: str, index: int, payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.keys.set_key(provider, index, payload.get("key", ""))

    @api.delete("/keys/{provider}/{index}")
    async def keys_remove(provider: str, index: int) -> Dict[str, Any]:
        return await state.keys.remove_key(provider, index)

    # ---- categorization / groups ----
    @api.get("/groups")
    async def groups_list() -> Dict[str, Any]:
        return await state.groups.list_groups()

    @api.get("/groups/state")
    async def groups_state() -> Dict[str, Any]:
        return state.groups.get_state()

    @api.get("/groups/{group_id}/topics")
    async def groups_topics(group_id: int) -> Dict[str, Any]:
        return await state.groups.list_topics(group_id)

    @api.put("/groups/target")
    async def groups_target(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return state.groups.set_target(int(payload.get("group_id")))

    @api.post("/groups/mappings")
    async def groups_add_map(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return state.groups.add_mapping(payload.get("command", ""), int(payload.get("topic_id")))

    @api.delete("/groups/mappings")
    async def groups_clear() -> Dict[str, Any]:
        return state.groups.clear()

    @api.delete("/groups/mappings/{command}")
    async def groups_del_map(command: str) -> Dict[str, Any]:
        return state.groups.remove_mapping(command)

    # ---- tts voices ----
    @api.get("/tts/voices")
    async def tts_voices() -> Dict[str, Any]:
        return state.status.tts_voices()

    @api.get("/models")
    async def models() -> Dict[str, Any]:
        return state.status.models()

    @api.get("/help")
    async def help_() -> Dict[str, Any]:
        return state.status.help()

    # ---- onboarding / first-run setup ----
    @api.get("/setup/status")
    async def setup_status() -> Dict[str, Any]:
        if not state.onboarding:
            return {"ok": True, "needs_setup": False}
        return state.onboarding.status()

    @api.post("/setup/start")
    async def setup_start(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.onboarding.start(
            payload.get("api_id"), payload.get("api_hash", ""), payload.get("phone", "")
        )

    @api.post("/setup/code")
    async def setup_code(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.onboarding.submit_code(payload.get("code", ""))

    @api.post("/setup/password")
    async def setup_password(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.onboarding.submit_password(payload.get("password", ""))

    @api.post("/setup/finalize")
    async def setup_finalize(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.onboarding.finalize(payload.get("llm"))

    # ---- dialogs ----
    @api.get("/dialogs")
    async def dialogs(
        type: str = "all", q: Optional[str] = None, offset: int = 0, limit: int = 200
    ) -> Dict[str, Any]:
        return await state.dialogs.list_dialogs(kind=type, q=q, offset=offset, limit=limit)

    @api.post("/dialogs/refresh")
    async def dialogs_refresh(type: str = "all") -> Dict[str, Any]:
        return await state.dialogs.list_dialogs(kind=type, force_refresh=True)

    # ---- entity ----
    @api.get("/entity/{entity_id}")
    async def entity_detail(entity_id: int) -> Dict[str, Any]:
        return await state.entity.detail(entity_id)

    @api.get("/entity/{entity_id}/profile")
    async def entity_profile(entity_id: int) -> Dict[str, Any]:
        return await state.entity.profile(entity_id)

    @api.get("/entity/{entity_id}/history")
    async def entity_history(
        entity_id: int,
        limit: int = 30,
        before_id: Optional[int] = None,
        after_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        return await state.entity.history(
            entity_id, limit=limit, before_id=before_id, after_id=after_id
        )

    @api.post("/entity/{entity_id}/send")
    async def entity_send(
        entity_id: int, payload: Dict[str, Any] = Body(default={})
    ) -> Dict[str, Any]:
        return await state.messenger.send_text(
            entity_id, payload.get("text", ""), payload.get("reply_to")
        )

    @api.post("/entity/{entity_id}/send-file")
    async def entity_send_attachment(
        entity_id: int,
        request: Request,
        file: UploadFile = File(...),
        caption: str = Form(default=""),
        reply_to: Optional[int] = Form(default=None),
    ) -> Dict[str, Any]:
        from .services.messenger_service import MAX_FILE_BYTES

        # Reject early if the declared size already blows the cap...
        clen = request.headers.get("content-length")
        if clen and clen.isdigit() and int(clen) > MAX_FILE_BYTES + (1 << 20):
            raise PanelError("File too large.", status_code=413)
        # ...then read with a hard ceiling so an absent/lying Content-Length
        # can't make us buffer an unbounded body into memory.
        buf = bytearray()
        while True:
            chunk = await file.read(256 * 1024)
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > MAX_FILE_BYTES:
                raise PanelError(
                    f"File too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB).",
                    status_code=413,
                )
        return await state.messenger.send_attachment(
            entity_id, bytes(buf), file.filename or "file", caption, reply_to
        )

    @api.get("/entity/{entity_id}/media")
    async def entity_media(
        entity_id: int, kind: str = "all", limit: int = 24, before_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return await state.entity.media(entity_id, kind=kind, limit=limit, before_id=before_id)

    # ---- media streaming (binary) ----
    @api.get("/avatar/{entity_id}")
    async def avatar(entity_id: int, real: int = 0) -> Response:
        if real and state.panel_config.real_photos and state.client_ready():
            path = await state.entity.real_avatar_path(entity_id)
            if path:
                return FileResponse(path, media_type="image/jpeg")
        name = (state.dialogs.find(entity_id) or {}).get("display_name", "")
        return Response(content=initials_svg(entity_id, name), media_type="image/svg+xml")

    @api.get("/entity/{entity_id}/media/{message_id}/thumb")
    async def media_thumb(entity_id: int, message_id: int) -> Response:
        info = await state.entity.media_file(entity_id, message_id, thumb=True)
        return FileResponse(info["path"], media_type=info["mime"] or "image/jpeg")

    @api.get("/entity/{entity_id}/media/{message_id}/file")
    async def media_file(entity_id: int, message_id: int) -> Response:
        info = await state.entity.media_file(entity_id, message_id, thumb=False)
        mime = info["mime"] or "application/octet-stream"
        # Telegram media comes from arbitrary peers. Anything that isn't a plain
        # image/audio/video is served as a forced download so a crafted HTML or
        # SVG document can't render (and run script) same-origin in the panel.
        headers: Dict[str, str] = {}
        if not (mime.startswith(("image/", "audio/", "video/")) and mime != "image/svg+xml"):
            headers["Content-Disposition"] = _attachment_disposition(Path(info["path"]).name)
        return FileResponse(info["path"], media_type=mime, headers=headers)

    # ---- live channel (SSE): typing / presence / new messages ----
    @api.get("/events")
    async def events_stream(request: Request, entity_id: Optional[int] = None) -> StreamingResponse:
        from .events import TooManySubscribers

        try:
            sub = state.events.subscribe(entity_id)
        except TooManySubscribers:
            raise PanelError("Too many live connections.", status_code=503)

        async def gen():
            try:
                yield ": connected\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        ev = await asyncio.wait_for(sub.queue.get(), timeout=15)
                        yield f"data: {json.dumps(ev, default=str)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"  # heartbeat keeps the connection alive
            except asyncio.CancelledError:
                pass  # client closed or server is shutting down — exit quietly
            finally:
                state.events.unsubscribe(sub)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive",
        })

    # ---- commands ----
    @api.post("/cmd/prompt")
    async def cmd_prompt(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_prompt(
            payload.get("text", ""),
            think=bool(payload.get("think")),
            web=bool(payload.get("web")),
        )

    @api.post("/cmd/translate")
    async def cmd_translate(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_translate(
            payload.get("text", ""),
            payload.get("target_lang", ""),
            payload.get("source", "auto"),
        )

    @api.post("/cmd/analyze")
    async def cmd_analyze(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_analyze(
            int(payload.get("entity_id")),
            count=int(payload.get("count", 100)),
            mode=payload.get("mode", "general"),
            language=payload.get("language", "persian"),
            think=bool(payload.get("think")),
        )

    @api.post("/cmd/tellme")
    async def cmd_tellme(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_tellme(
            int(payload.get("entity_id")),
            payload.get("question", ""),
            count=int(payload.get("count", 100)),
            think=bool(payload.get("think")),
            web=bool(payload.get("web")),
        )

    @api.post("/cmd/image")
    async def cmd_image(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_image(payload.get("model", "flux"), payload.get("prompt", ""))

    @api.post("/cmd/tts")
    async def cmd_tts(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_tts(payload.get("text", ""), payload.get("voice"))

    @api.post("/cmd/stt")
    async def cmd_stt(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.commands.run_stt(
            int(payload.get("entity_id")), int(payload.get("message_id"))
        )

    @api.get("/cmd/result-media/{token}")
    async def result_media(token: str) -> Response:
        info = state.result_tokens.get(token)
        if not info:
            raise PanelNotFound("Result expired or not found.")
        return FileResponse(info["path"], media_type=info["mime"])

    # ---- authorized users ----
    @api.get("/auth")
    async def auth_list() -> Dict[str, Any]:
        return state.auth.list_authorized()

    @api.post("/auth")
    async def auth_add(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
        return await state.auth.add(payload.get("identifier", ""))

    @api.delete("/auth/{user_id}")
    async def auth_remove(user_id: int) -> Dict[str, Any]:
        return state.auth.remove(user_id)

    app.include_router(api)

    # ---- static SPA (unauthenticated shell) served last so /api wins ----
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app
