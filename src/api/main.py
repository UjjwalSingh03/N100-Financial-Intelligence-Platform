"""Sprint 6 Day 38: FastAPI scaffold.

Start: uvicorn src.api.main:app --port 8000
CORS wildcard is intended for internal-only deployments.
"""
import logging
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.routers import companies, screener, sectors, peers, valuation, portfolio, documents, health

VERSION = "0.1.0"
STARTED_AT = time.monotonic()
logger = logging.getLogger("n100.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="N100 Financial Intelligence API", version=VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_logging(request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("method=%s path=%s duration_ms=%.2f status=500",
                         request.method, request.url.path, (time.perf_counter()-started)*1000)
        raise
    logger.info("method=%s path=%s duration_ms=%.2f status=%s",
                request.method, request.url.path, (time.perf_counter()-started)*1000,
                response.status_code)
    return response


@app.exception_handler(FileNotFoundError)
async def missing_database(request, exc: FileNotFoundError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


for router in (companies.router, screener.router, sectors.router, peers.router,
               valuation.router, portfolio.router, documents.router, health.router):
    app.include_router(router, prefix="/api/v1")
