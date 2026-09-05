from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modules.backend.src.api.rest import router as rest_router
from modules.backend.src.api.ws import router as ws_router
from modules.backend.src.config import settings

app = FastAPI(
    title=settings.app_name,
    description="Thin API and WS relay for Shikshak AI Backend",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount both with /api/v1 prefix and root prefix for maximum client compatibility
app.include_router(rest_router, prefix=settings.api_v1_str)
app.include_router(ws_router, prefix=settings.api_v1_str)
app.include_router(rest_router)
app.include_router(ws_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
