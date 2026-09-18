import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.charts import router as charts_router
from app.api.v1.connections import router as connection_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.deploy import router as deploy_router
from app.api.v1.internal import router as internal_router
from app.api.v1.metadata import router as metadata_router
from app.core.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="MetaConnect", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong on our end. Please try again."},
    )


app.include_router(deploy_router, prefix="/api")
app.include_router(connection_router, prefix="/api")
app.include_router(metadata_router, prefix="/api")
app.include_router(internal_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(charts_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}