from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Health"])


@router.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redirect root endpoint to API documentation."""
    return RedirectResponse(url="/docs")


@router.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}
