from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.services.identity_router import IdentityRouter
from app.services.text_checker import TextChecker
from app.services.voice_profiles import VoiceProfileService
from app.services.brand_tokens import BrandTokenService

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
identity_router = IdentityRouter()
text_checker = TextChecker()
voice_service = VoiceProfileService()
brand_token_service = BrandTokenService()


# --- Identity Router ---

@router.get("/identity")
async def identity_page(request: Request):
    return templates.TemplateResponse("brand/identity_router.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "contexts": identity_router.all_contexts(),
        "results": None,
        "query": "",
    })


@router.post("/identity/search")
async def identity_search(request: Request, query: str = Form("")):
    results = identity_router.search(query) if query.strip() else []
    # HTMX partial response
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("brand/_identity_results.html", {
            "request": request,
            "results": results,
            "query": query,
        })
    return templates.TemplateResponse("brand/identity_router.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "contexts": identity_router.all_contexts(),
        "results": results,
        "query": query,
    })


# --- Text Checker ---

@router.get("/checker")
async def checker_page(request: Request):
    voices = voice_service.list_profiles()
    return templates.TemplateResponse("brand/text_checker.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "voices": voices,
        "results": None,
        "text": "",
        "selected_voice": "",
    })


@router.post("/checker/analyze")
async def checker_analyze(
    request: Request,
    text: str = Form(""),
    voice_id: str = Form(""),
):
    results = text_checker.check(text, voice_id) if text.strip() else None
    voices = voice_service.list_profiles()
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("brand/_checker_results.html", {
            "request": request,
            "results": results,
            "text": text,
        })
    return templates.TemplateResponse("brand/text_checker.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "voices": voices,
        "results": results,
        "text": text,
        "selected_voice": voice_id,
    })


# --- Real-time check (Tier 1 only, for drafting workspace) ---

@router.post("/api/check-realtime")
async def check_realtime(request: Request, text: str = Form(""), voice_id: str = Form("")):
    if not text.strip():
        return {"violations": []}
    violations = text_checker.check_tier1(text, voice_id)
    return {"violations": [v.model_dump() for v in violations]}


# --- Voice Profiles ---

@router.get("/voices")
async def voices_page(request: Request):
    profiles = voice_service.list_profiles()
    return templates.TemplateResponse("brand/voice_profiles.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "profiles": profiles,
    })


@router.patch("/voices/{voice_id}")
async def update_voice(voice_id: str, request: Request):
    body = await request.json()
    updated = voice_service.update_profile(voice_id, body)
    if updated:
        return {"status": "ok", "voice_id": voice_id}
    return {"status": "error", "message": "Voice profile not found"}


# --- Brand Library ---

@router.get("/tokens")
async def tokens_page(request: Request):
    tokens = brand_token_service.list_tokens()
    # Deduplicated Google Fonts list from all tokens
    google_fonts = []
    seen = set()
    for token in tokens:
        for font in (token.get("typography") or []):
            if font.get("source") == "google_fonts" and font["font"] not in seen:
                google_fonts.append(font["font"])
                seen.add(font["font"])
    return templates.TemplateResponse("brand/brand_library.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "tokens": tokens,
        "google_fonts": google_fonts,
    })


@router.patch("/tokens/{context_id}")
async def update_token(context_id: str, request: Request):
    body = await request.json()
    updated = brand_token_service.update_token(context_id, body)
    if updated:
        return {"status": "ok", "context_id": context_id}
    return {"status": "error", "message": "Token not found"}


# --- Drafting Workspace ---

@router.get("/drafting")
async def drafting_page(request: Request):
    voices = voice_service.list_profiles()
    contexts = identity_router.all_contexts()
    return templates.TemplateResponse("brand/drafting.html", {
        "request": request,
        "modules": request.state.modules,
        "active_module": "brand",
        "voices": voices,
        "contexts": contexts,
    })
