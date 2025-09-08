from fastapi import APIRouter
router = APIRouter()

@router.get("/health")
def health():
    return {"status":"ok"}       # Just a simple health check endpoint
