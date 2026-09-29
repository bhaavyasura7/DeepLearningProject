from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.interactions import router as interactions_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.movies import router as movies_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.settings import router as settings_router
from app.config import settings

app = FastAPI(
    title="Proactive Movie Recommendation System",
    description="Agentic AI-based Proactive Recommendation System using Dynamic User Preference Memory",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "llm_provider": settings.LLM_PROVIDER,
    }


# Include versioned API v1 routers
v1_prefix = "/api/v1"

from fastapi import Depends
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.auth_service import get_current_user

@app.get(f"{v1_prefix}/me", response_model=UserResponse, tags=["auth"])
def get_current_user_profile(user: User = Depends(get_current_user)):
    return user

app.include_router(auth_router, prefix=v1_prefix)
app.include_router(movies_router, prefix=v1_prefix)
app.include_router(interactions_router, prefix=v1_prefix)
app.include_router(recommendations_router, prefix=v1_prefix)
app.include_router(preferences_router, prefix=v1_prefix)
app.include_router(settings_router, prefix=v1_prefix)
app.include_router(notifications_router, prefix=v1_prefix)
app.include_router(jobs_router, prefix=v1_prefix)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Ensure no secrets or sensitive stack traces leak to users
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )
