"""FastAPI app factory for the SakaiBot control panel.

Thin layer: each route delegates to a service method and returns its dict.
No business logic here. Static SPA is served unauthenticated (it's just the
shell); every ``/api/*`` route except ``/api/health`` requires the token.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from ..utils.logging import get_logger
from .auth import require_token
from .avatars import initials_svg
from .errors import PanelError, PanelNotFound, PanelUnavailable

logger = get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


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
        return state.status.keys()

    @api.get("/models")
    async def models() -> Dict[str, Any]:
        return state.status.models()

    @api.get("/help")
    async def help_() -> Dict[str, Any]:
        return state.status.help()

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

    @api.get("/entity/{entity_id}/history")
    async def entity_history(
        entity_id: int, limit: int = 30, before_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return await state.entity.history(entity_id, limit=limit, before_id=before_id)

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
        return FileResponse(info["path"], media_type=info["mime"])

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
