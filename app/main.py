from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.settings import settings
from .routers import routes, orders, matches
from .routers import auth, workers, employers, admin, matching
from .db import Base, engine

# Create all Partimer tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Partimer API",
    description="WhatsApp-First Part-Time Worker Lead Marketplace Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/")
def root():
    return {
        "app": "Partimer API",
        "version": "1.0.0",
        "description": "WhatsApp-First Part-Time Worker Lead Marketplace"
    }

# Legacy Koridor routes (for backward compatibility)
app.include_router(routes.router, prefix="/routes", tags=["Legacy: Routes"])
app.include_router(orders.router, prefix="/orders", tags=["Legacy: Orders"])
app.include_router(matches.router, prefix="/routes", tags=["Legacy: Matches"])

# Partimer routes - Role-based separation
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(workers.router, prefix="/api/workers", tags=["Workers"])
app.include_router(employers.router, prefix="/api/employers", tags=["Employers"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(matching.router, prefix="/api/matching", tags=["Matching"])
