"""Local bearer-token auth for the panel.

Token is accepted either as ``Authorization: Bearer <token>`` (fetch calls) or
as a ``?t=<token>`` query param (so <img>/<audio> tags can authenticate, since
browsers can't set headers on those). Constant-time comparison.
"""

import hmac

from fastapi import Header, HTTPException, Query, Request


async def require_token(
    request: Request,
    authorization: str = Header(default=""),
    t: str = Query(default=""),
) -> bool:
    expected = request.app.state.panel.panel_config.token
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = t or ""
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return True
