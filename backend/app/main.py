from dotenv import load_dotenv
load_dotenv()  # 加载 backend/.env 中的 AMAP_KEY

import logging
import time

from fastapi import FastAPI, Request as FastAPIRequest
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

logger = logging.getLogger(__name__)

app = FastAPI(title="P003 Mock API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.middleware("http")
async def log_request_time(request: FastAPIRequest, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - t0) * 1000)
    if ms > 3000:
        logger.warning("SLOW %s %s %dms", request.method, request.url.path, ms)
    elif ms > 1000:
        logger.info("SLOW-ish %s %s %dms", request.method, request.url.path, ms)
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
