from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.qa import router as qa_router
from app.api.actions import router as actions_router

app = FastAPI(title="AR Agentic Backend")

app.include_router(health_router)
app.include_router(qa_router)
app.include_router(actions_router)
