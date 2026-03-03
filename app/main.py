from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import APP_TITLE, STATIC_DIR, TEMPLATES_DIR
from app.routers import brand, calendar, dashboard, email, files, newsletter, revenue, tasks

app = FastAPI(title=APP_TITLE)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Module registry — each router registers its nav entry
MODULE_REGISTRY = [
    {"id": "dashboard", "label": "Home", "icon": "home", "path": "/"},
    {"id": "brand", "label": "Brand", "icon": "palette", "path": "/brand/identity"},
    {"id": "tasks", "label": "Tasks", "icon": "tasks", "path": "/tasks/"},
    {"id": "calendar", "label": "Calendar", "icon": "calendar", "path": "/calendar/"},
    {"id": "email", "label": "Email", "icon": "email", "path": "/email/"},
    {"id": "files", "label": "Files", "icon": "folder", "path": "/files/"},
    {"id": "newsletter", "label": "Newsletter", "icon": "newsletter", "path": "/newsletter/"},
    {"id": "revenue", "label": "Revenue", "icon": "revenue", "path": "/revenue/"},
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
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(email.router, prefix="/email", tags=["email"])
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(newsletter.router, prefix="/newsletter", tags=["newsletter"])
app.include_router(revenue.router, prefix="/revenue", tags=["revenue"])
