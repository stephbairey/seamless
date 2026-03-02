from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_TITLE, STATIC_DIR, TEMPLATES_DIR
from app.routers import brand, dashboard, tasks

app = FastAPI(title=APP_TITLE)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Module registry — each router registers its nav entry
MODULE_REGISTRY = [
    {"id": "dashboard", "label": "Home", "icon": "home", "path": "/"},
    {"id": "brand", "label": "Brand", "icon": "palette", "path": "/brand/identity"},
    {"id": "tasks", "label": "Tasks", "icon": "tasks", "path": "/tasks/"},
]

# Make registry available to all templates
@app.middleware("http")
async def inject_modules(request: Request, call_next):
    request.state.modules = MODULE_REGISTRY
    response = await call_next(request)
    return response

app.include_router(dashboard.router)
app.include_router(brand.router, prefix="/brand", tags=["brand"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
