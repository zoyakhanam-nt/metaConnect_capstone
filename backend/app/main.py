from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.connections import router as connection_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.deploy import router as deploy_router
from app.api.v1.internal import router as internal_router
from app.api.v1.metadata import router as metadata_router

app = FastAPI(title="MetaConnect", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deploy_router, prefix="/api")
app.include_router(connection_router, prefix="/api")
app.include_router(metadata_router, prefix="/api")
app.include_router(internal_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}