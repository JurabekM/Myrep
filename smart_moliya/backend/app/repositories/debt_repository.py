from app.models.debt import Debt
from app.repositories.base import BaseRepository


class DebtRepository(BaseRepository[Debt]):
    model = Debt
