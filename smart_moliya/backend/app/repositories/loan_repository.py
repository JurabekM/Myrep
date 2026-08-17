from app.models.loan import Loan
from app.repositories.base import BaseRepository


class LoanRepository(BaseRepository[Loan]):
    model = Loan
