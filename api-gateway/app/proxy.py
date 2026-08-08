"""
Rally API Gateway — Reverse proxy utilities.
"""

import logging
import httpx
from fastapi import Request, HTTPException, Response
from starlette.background import BackgroundTask

logger = logging.getLogger("rally.gateway.proxy")

client = httpx.AsyncClient(timeout=60.0)


async def proxy_request(request: Request, target_url: str) -> Response:
    """Proxy an incoming FastAPI request to a target URL."""
    try:
        url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
        target = f"{target_url}{url}"

        # Extract body if any
        content = await request.body()
        
        # Extract headers (filtering out host to avoid issues)
        headers = {
            k: v for k, v in request.headers.items() 
            if k.lower() not in ("host", "content-length")
        }

        # Send request
        rp_req = client.build_request(
            method=request.method,
            url=target,
            headers=headers,
            content=content,
        )
        rp_resp = await client.send(rp_req, stream=True)
        
        # Return response
        return Response(
            content=await rp_resp.aread(),
            status_code=rp_resp.status_code,
            headers={k: v for k, v in rp_resp.headers.items() if k.lower() != "content-encoding"},
            background=BackgroundTask(rp_resp.aclose),
        )

    except httpx.RequestError as e:
        logger.error("Proxy error to %s: %s", target_url, str(e))
        raise HTTPException(status_code=502, detail="Bad Gateway")
