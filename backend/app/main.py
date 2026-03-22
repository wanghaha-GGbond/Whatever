from dotenv import load_dotenv
load_dotenv()  # 加载 backend/.env 中的 AMAP_KEY

import logging
import os
import time
from uuid import uuid4

from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

logger = logging.getLogger(__name__)

app = FastAPI(title="P003 Mock API", version="0.1.0")


def _setup_logging() -> None:
    level = (os.getenv("LOG_LEVEL") or "INFO").strip().upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


_setup_logging()


def _allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if not raw:
        # 本地开发默认放行常见端口，生产请通过环境变量收口
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    origins = [x.strip() for x in raw.split(",") if x.strip()]
    return origins or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.middleware("http")
async def log_request_time(request: FastAPIRequest, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex[:12]}"
    request.state.request_id = request_id
    t0 = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        ms = round((time.monotonic() - t0) * 1000)
        logger.exception(
            "request_failed method=%s path=%s latency_ms=%d request_id=%s",
            request.method,
            request.url.path,
            ms,
            request_id,
        )
        raise

    ms = round((time.monotonic() - t0) * 1000)
    logger.info(
        "request method=%s path=%s status=%d latency_ms=%d request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        ms,
        request_id,
    )
    if ms > 3000:
        logger.warning("SLOW %s %s %dms", request.method, request.url.path, ms)
    elif ms > 1000:
        logger.info("SLOW-ish %s %s %dms", request.method, request.url.path, ms)
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
