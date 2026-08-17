from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, get_category_repository
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
async def list_categories(
    current_user: CurrentUser,
    repo: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> list[CategoryRead]:
    categories = await repo.list_for_user(current_user.id)
    return [CategoryRead.model_validate(c) for c in categories]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    current_user: CurrentUser,
    repo: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> CategoryRead:
    category = Category(user_id=current_user.id, name=payload.name, type=payload.type, icon=payload.icon)
    category = await repo.add(category)
    await repo.commit()
    return CategoryRead.model_validate(category)
