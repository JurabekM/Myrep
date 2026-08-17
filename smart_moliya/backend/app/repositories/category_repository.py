from sqlalchemy import or_, select

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    async def list_for_user(self, user_id) -> list[Category]:
        """Foydalanuvchi kategoriyalari + tizim standart kategoriyalari (user_id IS NULL)."""
        result = await self.session.execute(
            select(Category).where(or_(Category.user_id == user_id, Category.user_id.is_(None)))
        )
        return list(result.scalars().all())
