"""Content distribution endpoints — social copy generation."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.models.distribution import CopyRequest
from app.services.social_copy import social_copy_service

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "distribution",
        "active_tab": active_tab,
    }


# --- Home redirect ---

@router.get("/")
async def distribution_home(request: Request):
    return RedirectResponse(url="/distribution/generate", status_code=302)


# --- Generate ---

@router.get("/generate")
async def generate_page(request: Request):
    ctx = _base_ctx(request, "generate")
    ctx["batch"] = None
    ctx["configured"] = social_copy_service.is_configured
    return templates.TemplateResponse("distribution/generate.html", ctx)


@router.post("/generate")
async def generate_posts(
    request: Request,
    content: str = Form(""),
    brand: str = Form(""),
    url: str = Form(""),
    notes: str = Form(""),
):
    ctx = _base_ctx(request, "generate")

    if not content.strip():
        ctx["batch"] = None
        ctx["configured"] = social_copy_service.is_configured
        ctx["error"] = "Content is required."
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "distribution/_results_partial.html", ctx,
            )
        return templates.TemplateResponse("distribution/generate.html", ctx)

    if not brand:
        ctx["batch"] = None
        ctx["configured"] = social_copy_service.is_configured
        ctx["error"] = "Select a brand."
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                "distribution/_results_partial.html", ctx,
            )
        return templates.TemplateResponse("distribution/generate.html", ctx)

    try:
        copy_request = CopyRequest(
            content=content.strip(),
            brand=brand,
            url=url.strip(),
            notes=notes.strip(),
        )
        batch = await social_copy_service.generate_all_posts(copy_request)
        ctx["batch"] = batch
        ctx["content"] = content
        ctx["brand"] = brand
        ctx["url"] = url
        ctx["notes"] = notes
        ctx["error"] = None
    except Exception as e:
        logger.exception("Social copy generation failed")
        ctx["batch"] = None
        ctx["error"] = f"Generation failed: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "distribution/_results_partial.html", ctx,
        )
    return templates.TemplateResponse("distribution/generate.html", ctx)


# --- Regenerate marketing extras (must be before {platform} wildcard) ---

@router.post("/regenerate/seo")
async def regenerate_seo(
    request: Request,
    content: str = Form(""),
    brand: str = Form(""),
):
    ctx = _base_ctx(request, "generate")
    try:
        seo = await social_copy_service.regenerate_seo(content.strip(), brand)
        ctx["seo_description"] = seo
        ctx["content"] = content
        ctx["brand"] = brand
    except Exception as e:
        logger.exception("SEO regenerate failed")
        ctx["seo_description"] = f"(Regeneration failed: {e})"
        ctx["content"] = content
        ctx["brand"] = brand
    return templates.TemplateResponse("distribution/_extra_card.html", ctx)


@router.post("/regenerate/midjourney")
async def regenerate_midjourney(
    request: Request,
    content: str = Form(""),
    brand: str = Form(""),
):
    ctx = _base_ctx(request, "generate")
    try:
        mj = await social_copy_service.regenerate_midjourney(content.strip(), brand)
        ctx["midjourney_prompt"] = mj
        ctx["content"] = content
        ctx["brand"] = brand
    except Exception as e:
        logger.exception("Midjourney regenerate failed")
        ctx["midjourney_prompt"] = f"(Regeneration failed: {e})"
        ctx["content"] = content
        ctx["brand"] = brand
    return templates.TemplateResponse("distribution/_extra_card.html", ctx)


# --- Regenerate single platform ---

@router.post("/regenerate/{platform}")
async def regenerate_platform(
    request: Request,
    platform: str,
    content: str = Form(""),
    brand: str = Form(""),
    url: str = Form(""),
    notes: str = Form(""),
):
    ctx = _base_ctx(request, "generate")

    try:
        post = await social_copy_service.regenerate_single(
            brand=brand,
            platform=platform,
            content=content.strip(),
            url=url.strip(),
            notes=notes.strip(),
        )
        if not post:
            ctx["error"] = f"Platform '{platform}' not available for brand '{brand}'."
            ctx["post"] = None
        else:
            ctx["post"] = post
            ctx["content"] = content
            ctx["brand"] = brand
            ctx["url"] = url
            ctx["notes"] = notes
            ctx["error"] = None
    except Exception as e:
        logger.exception("Regenerate failed for %s", platform)
        ctx["post"] = None
        ctx["error"] = f"Regeneration failed: {e}"

    return templates.TemplateResponse(
        "distribution/_post_card.html", ctx,
    )
