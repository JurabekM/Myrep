"""Consultant endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import Container, CurrentUser
from app.modules.consultant.service import ConsultantService, Framework

router = APIRouter(prefix="/consultant", tags=["consultant"])


class GenerateRequest(BaseModel):
    framework: Framework
    business_description: str = Field(min_length=20, max_length=16_000)
    extra_context: str | None = Field(default=None, max_length=16_000)
    model: str | None = None


class GenerateResponse(BaseModel):
    framework: Framework
    content: str


@router.get("/frameworks")
async def frameworks(user: CurrentUser, container: Container) -> dict:
    service = ConsultantService(container.ai_router, container.prompts)
    return {"frameworks": service.frameworks()}


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    req: GenerateRequest, user: CurrentUser, container: Container
) -> GenerateResponse:
    service = ConsultantService(container.ai_router, container.prompts)
    content = await service.generate(
        user,
        req.framework,
        req.business_description,
        extra_context=req.extra_context,
        model=req.model,
    )
    return GenerateResponse(framework=req.framework, content=content)
