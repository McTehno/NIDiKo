from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.assessment_assistant import router as assessment_assistant_router
from app.api.assessments import router as assessments_router
from app.api.learning_path_assistant import router as learning_path_assistant_router
from app.api.learning_paths import router as learning_paths_router
from app.api.learning_unit_assistant import router as learning_unit_assistant_router
from app.api.learning_units import router as learning_units_router
from app.api.module_assistant import router as module_assistant_router
from app.api.modules import router as modules_router
from app.api.questionnaires import router as questionnaires_router
from app.api.search import router as search_router
from app.api.user_progress import router as user_progress_router
from app.api.users import router as users_router
from app.api.voice_help import router as voice_help_router
from app.core.error_handlers import (
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)

app = FastAPI(
    title="NIDiKo API",
    description="Backend API for the NIDiKo learning path recommendation system.",
    version="0.1.0",
)

# Registracija globalnih obravnavalnikov napak
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)

# Nastavitev CORS pravil za lokalno razvojno okolje in produkcijo
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5176",
        "http://localhost:3000",
        "http://46.225.17.135",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registracija domenskih API usmerjevalnikov
app.include_router(search_router, prefix="/api")
app.include_router(questionnaires_router, prefix="/api")
app.include_router(assessments_router, prefix="/api")
app.include_router(learning_paths_router, prefix="/api")
app.include_router(modules_router, prefix="/api")
app.include_router(learning_units_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(user_progress_router, prefix="/api")

# Registracija AI in glasovnih asistentov
app.include_router(voice_help_router, prefix="/api")
app.include_router(assessment_assistant_router, prefix="/api")
app.include_router(learning_path_assistant_router, prefix="/api")
app.include_router(module_assistant_router, prefix="/api")
app.include_router(learning_unit_assistant_router, prefix="/api")


@app.get("/")
def read_root() -> dict[str, str]:
    """
    Korenski preizkusni endpoint za preverjanje stanja delovanja backenda.
    """
    return {
        "message": "NIDiKo backend is running."
    }