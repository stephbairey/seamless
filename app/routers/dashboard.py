from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

GDRIVE_PROJECTS = Path("/mnt/g/My Drive/ALL PROJECTS")


@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "dashboard",
        "gdrive_mounted": GDRIVE_PROJECTS.is_dir(),
    })


@router.get("/health")
async def health():
    return {"status": "ok"}
